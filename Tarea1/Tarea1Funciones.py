#ejecuccion de plantilla y llamada de funciones de OpenIa
#tarea1
#Julio Alonso Garcia, ejemplo de test y ejecucion, basado en ejemplo de acceso a bd, usando una base de datos local. MSSQL Server Express

from openai import OpenAI
from datetime import datetime, timedelta
from DataBase import Database
import json
#base de datos local de MSSQL Express
_database = Database(
    host='(local)',
    user='sa',
    password='1234',
    database='SFS'
)

class OpenAIAssistant:
    def __init__(self, api_key, timeout_minutes=30):
        self.client = OpenAI(api_key='API KEY')
        self.messages = [
                {"role": "system", "content": "Eres un empleado bilingüe de EISEI que ayuda a los clientes con información de los reportes de oportunidad. Tu función es brindar información clara sobre los reportes de oportunidad, no buscas informacion en internet ni nada que no sea de la empresa EISEI." },
            ]
        self.last_interaction_time = datetime.now()
        self.timeout = timedelta(minutes=timeout_minutes)


    def clear_messages_if_timeout(self):
        if datetime.now() - self.last_interaction_time > self.timeout:
            self.messages = [self.messages[0]] 

    def handle_message(self, question_user):
        self.clear_messages_if_timeout()
        self.last_interaction_time = datetime.now()
        
        if "hola" in question_user.lower():
            menu_message = "¡Hola! 👋 ¿En qué puedo ayudarte hoy?\n1. Ver los reportes del día\n2. Ver los reportes de la semana"
            self.messages.append({"role": "user", "content": menu_message})
           
            return menu_message
        
        self.messages.append({"role": "user", "content": question_user})
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=self.messages,
            tools=[
                {
                        "type": "function",
                        "function": {
                            "name": "query_empresa",
                            "description": "Query the company ID based on its name and return an idEmpresa along with its NombreEmpresa according to the specified company, and return a type of report, either weekly or daily, as requested by the user.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "data": {
                                        "type": "array",
                                        "description": "The JSON data to query",
                                        "items": {
                                            "type": "object"
                                        }
                                    },
                                    "query": {
                                        "type": "object",
                                        "description": "The query parameters",
                                        "properties": {
                                           
                                            "NombreEmpresa": {"type": "string"},
                                            "TipoReporte": {"type": "string"}
                                        }
                                    }
                                },
                                "required": ["query"]
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "query_oportinudades",
                            "description": "Query the company's ongoing opportunities based on its name and return that data as needed according to the user's request.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "data": {
                                        "type": "array",
                                        "description": "The JSON data to query",
                                        "items": {
                                            "type": "object"
                                        }
                                    },
                                    "query": {
                                        "type": "object",
                                        "description": "The query parameters",
                                        "properties": {
                                            "NombreSector": {"type": "string"},
                                            "NombreProspecto": {"type": "string"},
                                            "NombreOportunidad": {"type": "string"},
                                            "ArchivoDescripcion": {"type": "string"},
                                            "AbreviaturaTipoOportunidad": {"type": "string"},
                                            "DescripcionTipoOportunidad": {"type": "string"},
                                            "Entrega": {"type": "string"},
                                            "EntregaDescripcion": {"type": "string"},
                                            "Iniciales": {"type": "string"},
                                            "NombreContacto": {"type": "string"},
                                            "NombreEjecutivo": {"type": "string"},
                                            "Monto": {"type": "number"},
                                            "Probabilidad": {"type": "string"},
                                            "DiasSinActividad": {"type": "number"},
                                            "Comentario": {"type": "string"},
                                            "MontoNormalizado": {"type": "number"},
                                            "FechaRegistro": {"type": "string"},
                                            "FechaRegistroDate": {"type": "string"},
                                            "AbreviaturaEstatus": {"type": "string"},
                                            "DescripcionEstatus": {"type": "string"},
                                            "FechaEstimadaCierreUpd": {"type": "string"},
                                            "FechaEstimadaCierre": {"type": "string"},
                                            "ProbabilidadOriginal": {"type": "string"},
                                            "DiasFunnel": {"type": "number"},
                                            "TooltipStage": {"type": "string"},
                                            "TotalComentarios": {"type": "number"},
                                            "TotalArchivos": {"type": "number"},
                                            "IdTipoProyecto": {"type": "number"},
                                            "IdTipoEntrega": {"type": "number"}
                                           
                                        }
                                    }
                                },
                                "required": ["query"]
                            }
                        }
                    }
                ],
            tool_choice="auto"
        )
        response_message = response.choices[0].message
        print(response_message)
        tool_calls = response_message.tool_calls
       
        print(tool_calls)
        if tool_calls:
            available_functions = {
                "query_empresa": _database.query_empresa,
                "query_oportinudades": _database.query_oportinudades,

            }
            self.messages.append(response_message)

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                print(function_args)
                if function_name == "query_empresa":
                    function_response = function_to_call(
                        query= function_args.get("query")
                    )
                    #print(function_response)
                elif function_name == "query_oportinudades":
                    function_response = function_to_call(
                        query= function_args.get("query")
                    )
                
                # Verifica si la respuesta es una cadena JSON y conviértela a un diccionario si es necesario
                if isinstance(function_response, str):
                    try:
                        function_response = json.loads(function_response)
                        print("Function Response (Converted to Dict):")  # Imprime después de convertir
                    except json.JSONDecodeError:
                        print("Error decoding JSON from function response.")
                        function_response = {"status": "error", "message": "Error al procesar la respuesta."}
                
                # Verifica si es un diccionario y si contiene la clave "result"
                if isinstance(function_response, dict):
                    if "message" in function_response:
                        
                        function_response = self.truncate_result_if_needed(function_response)
                        
                        print( function_response)  # Imprime después de truncar
                    else:
                        print('Key "result" not found in function_response.')
                        function_response = json.dumps({"status": "error", "message": "No se encontró la información o el formato es incorrecto."})
                else:
                    print('Function Response is not a dictionary.')
                    function_response = json.dumps({"status": "error", "message": "No se encontró la información o el formato es incorrecto."})

                if not function_response:
                    function_response = json.dumps({"status": "success", "message": "No tengo esa informacion"})
                
            self.messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                        
                    }
                )
            second_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=self.messages,
            )
            
            if second_response.choices:
                return second_response.choices[0].message.content
        
        else:
            print(response_message)
            return response_message.content
        
    def truncate_result_if_needed(self, response_dict):
        max_tokens = 1000 
        try:
            if "message" in response_dict:
                result_text = response_dict["message"]
                if isinstance(result_text, str):
                    words = result_text.split()
                    if len(words) > max_tokens:
                        truncated_result = ' '.join(words[:max_tokens]) + '...'
                        response_dict["message"] = truncated_result
                else:
                   
                    response_dict["message"] = "Contenido no válido para truncar."
                    #print(response_dict)
            return json.dumps(response_dict)
        except Exception as e:
            print(e)
            return json.dumps({"status": "error", "message": f"Error al truncar el contenido: {str(e)}"})
        
if __name__ == "__main__":
    '''
        Recepción de la Solicitud (question_user):
        El modelo recibe la solicitud de entrada, que puede incluir instrucciones, preguntas o comandos. Esta entrada puede estar estructurada en lenguaje natural o ser un comando explícito que requiere ejecutar una función específica.
    '''
    question_user = input("Ingresa tu pregunta: ")
    assistant = OpenAIAssistant(question_user)
     
    answer = assistant.handle_message(question_user)
    print(answer)
