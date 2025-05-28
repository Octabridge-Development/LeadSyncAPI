# function_app.py
import azure.functions as func
import logging
import os

# Configuración de logging muy básica para ver si este archivo se ejecuta
# Azure Functions debería capturar prints y logging.info/error en Application Insights
# y en el Log Stream si está conectado.
print("PRINT: function_app.py - INICIO DE EJECUCIÓN DEL ARCHIVO")
logging.basicConfig(level=logging.DEBUG) # Intenta establecer el nivel aquí también
logging.debug("DEBUG: function_app.py - Logging configurado a DEBUG.")
logging.info("INFO: function_app.py - Archivo siendo procesado.")

# Variable para ver si la app FastAPI se carga
fastapi_app_loaded = False
initialization_error_message = "No error"

try:
    logging.info("INFO: Intentando importar 'app' desde 'app.main'")
    print("PRINT: Intentando importar 'app' desde 'app.main'")
    from app.main import app as fastapi_application  # Renombrado para claridad
    fastapi_app_loaded = True
    logging.info("INFO: 'app' importada exitosamente desde 'app.main'.")
    print("PRINT: 'app' importada exitosamente desde 'app.main'.")

except ImportError as ie:
    initialization_error_message = f"ImportError: {str(ie)}"
    logging.error(f"ERROR DE IMPORTACIÓN: {initialization_error_message}", exc_info=True)
    print(f"PRINT: ERROR DE IMPORTACIÓN: {initialization_error_message}")
except Exception as e:
    initialization_error_message = f"Exception: {str(e)}"
    logging.error(f"ERROR GENERAL AL IMPORTAR/CONFIGURAR: {initialization_error_message}", exc_info=True)
    print(f"PRINT: ERROR GENERAL AL IMPORTAR/CONFIGURAR: {initialization_error_message}")

# Crear la FunctionApp principal
azure_functions_app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

if fastapi_app_loaded:
    logging.info("INFO: Envolviendo la aplicación FastAPI con AsgiFunctionApp.")
    print("PRINT: Envolviendo la aplicación FastAPI con AsgiFunctionApp.")
    # Esta es la forma de exponer tu app FastAPI a través de Azure Functions
    # El nombre de la variable 'app_func' no es especial, pero es común.
    # Lo importante es que el objeto AsgiFunctionApp se registre con el worker.
    # Azure Functions buscará funciones decoradas o un objeto AsgiFunctionApp.
    # Al no usar decoradores aquí, el objeto AsgiFunctionApp es el que se sirve.
    # Si esto se hace, no necesitas el @azure_functions_app.route("/diag") de abajo.
    # Sin embargo, para que Azure Functions lo "vea" sin decoradores,
    # el objeto AsgiFunctionApp debe ser asignado a una variable que el worker pueda descubrir,
    # o ser el resultado de la ejecución del script si es el único objeto de función.
    # La documentación sugiere que el worker de Python escanea el archivo.
    # Para ser explícitos, podrías intentar asignar el resultado de AsgiFunctionApp
    # a una variable conocida o simplemente dejar que el worker lo encuentre.
    # Vamos a probar manteniendo la variable global `azure_functions_app` y
    # si FastAPI carga, la reemplazamos o hacemos que AsgiFunctionApp sea el principal.

    # El modelo de programación v2 espera que las funciones estén registradas
    # en un objeto FunctionApp. Si AsgiFunctionApp es tu única "función",
    # debería ser suficiente.
    # Vamos a reasignar `azure_functions_app` para que sea el AsgiFunctionApp
    azure_functions_app = func.AsgiFunctionApp(app=fastapi_application, http_auth_level=func.AuthLevel.ANONYMOUS)
    logging.info("INFO: AsgiFunctionApp configurado como el manejador principal.")
    print("PRINT: AsgiFunctionApp configurado como el manejador principal.")

else:
    logging.warning("ADVERTENCIA: La aplicación FastAPI no se cargó. Se expondrá solo el endpoint de diagnóstico.")
    print("PRINT: ADVERTENCIA: La aplicación FastAPI no se cargó. Se expondrá solo el endpoint de diagnóstico.")

    @azure_functions_app.route(route="diag")
    def diagnostic_endpoint(req: func.HttpRequest) -> func.HttpResponse:
        logging.info("INFO: Endpoint de diagnóstico accedido.")
        print("PRINT: Endpoint de diagnóstico accedido.")
        if fastapi_app_loaded:
            status_msg = "FastAPI app parece estar cargada (pero este endpoint no debería ser llamado si AsgiFunctionApp está activo)."
        else:
            status_msg = f"FastAPI app NO se cargó. Error: {initialization_error_message}"

        return func.HttpResponse(
            f"Mensaje de diagnóstico:\n{status_msg}\n"
            f"FUNCTIONS_WORKER_RUNTIME: {os.getenv('FUNCTIONS_WORKER_RUNTIME')}\n"
            f"WEBSITE_SITE_NAME: {os.getenv('WEBSITE_SITE_NAME')}\n",
            status_code=200 if fastapi_app_loaded else 500
        )
    logging.info("INFO: Endpoint de diagnóstico /diag registrado.")
    print("PRINT: Endpoint de diagnóstico /diag registrado.")

logging.info("INFO: function_app.py - FIN DE EJECUCIÓN DEL ARCHIVO")
print("PRINT: function_app.py - FIN DE EJECUCIÓN DEL ARCHIVO")