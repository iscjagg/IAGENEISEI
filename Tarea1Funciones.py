#ejecuccion de plantilla y llamada de funciones de OpenIa
#tarea1
#Julio Alonso Garcia, ejemplo de test y ejecucion, basado en ejemplo de acceso a bd, usando una base de datos local. MSSQL Server Express

from openai import OpenAI
from datetime import datetime, timedelta
import json

class OpenAIAssistant:
    def __init__(self, question_user):
        self.client = OpenAI(api_key='poner Key openia')
        #Lista de mensajes guardados en el hilo
        self.messages = [
                {"role": "system", "content": "Eres un empleado bilingüe de EISEI que ayuda a los clientes con información de los reportes de oportunidad. Tu función es brindar información clara sobre los reportes de oportunidad, no buscas informacion en internet ni nada que no sea de la empresa EISEI." },
        ]
     
        self.messages.append({"role": "user", "content": question_user})

    def get_response(self):
            #estructura para generar respuesta que genera openai 
            #PASO 1 Su aplicación llama a la API con su solicitud y definiciones de las funciones que el LLM puede llamar
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=self.messages,
                #Definicion de funciones dentro de las herramientas (tools)
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
                        }
                    ],
                tool_choice="auto"
            )
            #respuesta completa generada
            print(response)
            response_message = response.choices[0].message
            print(response_message)

            #PASO 2 El modelo decide si responder al usuario o si se debe llamar a una o más funciones.
            #El modelo analiza el contenido de la solicitud para determinar si se requiere una llamada a función. Identifica las posibles funciones a ejecutar basándose en las intenciones del usuario y en el formato de los datos recibidos.
            #recolectar las funciones de las respuestas
            tool_calls = response_message.tool_calls
            print(tool_calls)
            
            
            #si hay llamada a la funcion
            if tool_calls:
                
                #PASO 3 La API responde a su aplicación especificando la función a llamar y los argumentos para llamarla con:
                # Una vez identificada la función, el modelo prepara los datos necesarios para su ejecución (como argumentos específicos) y luego invoca la función correspondiente. La función ejecuta su tarea y produce un resultado o un conjunto de datos.
                
                available_functions = {
                    "query_empresa": Database().query_empresa, #mapea las funciones a las funciones de la base de datos
                }
                self.messages.append(response_message)

                for tool_call in tool_calls: #Busca la funcion correspondiente
                    function_name = tool_call.function.name #obtiene el nombre de la funcion que se llamo
                    function_to_call = available_functions[function_name] #busca la funcion asignada la clase de Database
                    function_args = json.loads(tool_call.function.arguments)
                    print(function_args)
                    if function_name == "query_empresa":
                        #PASO 4 Su aplicación ejecuta la función con los argumentos dados
                        #va a la funcion de query_empresa en la clase DataBase y ejecuta la funcion 
                        function_response = function_to_call( 
                            query= function_args.get("query")
                        )
                        
                #Tras la ejecución de la función, el resultado o la respuesta generada (fuction_response) es recogida y organizada. Si la función devuelve un resultado estructurado, como un JSON o un texto específico, se prepara para su inclusión en la respuesta final del modelo.
                self.messages.append( #agrega a la lista de mensajes la respuesta a esa funcion por medio de su id
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response,    
                        }
                        
                    )
                #genera una respuesta en base a lo que se contesto en la funcion
                #PASO 5 Su aplicación llama a la API que proporciona su mensaje y el resultado de la función llama a su código que acaba de ejecutar
                second_response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=self.messages,
                )
                #regresa al usuario esa respuesta
                if second_response.choices:
                    return second_response.choices[0].message.content
            #si no se llaman funciones genera una repsuesta normal
            else:
                print(response_message)
                return response_message.content
    

#CLASE   
import pyodbc
from decimal import Decimal
from fuzzywuzzy import fuzz, process
import json
from datetime import datetime

class Database:
    def __init__(self):
        self.host = '(local)'
        self.user = 'sa'
        self.password = 'Contraseña' #especificar contraseña de bd local
        self.database = 'SFS'

    def execute_sql_query(self, query):
        try:
            #conexion a la base de datos
            connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.host};DATABASE={self.database};UID={self.user};PWD={self.password}'
            
            conn = pyodbc.connect(connection_string)
            cursor = conn.cursor()
            
            cursor.execute(query)
            
            # Obtener resultados
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            result = []
            for row in rows:
                row_dict = {}
                for i, column in enumerate(columns):
                    value = row[i]
                    # Convertir Decimals a float, datetime a str
                    if isinstance(value, Decimal):
                        value = float(value)
                    elif isinstance(value, datetime):
                        value = value.isoformat()  # Convertir datetime a cadena en formato ISO
                    row_dict[column] = value
                result.append(row_dict)
            
            # Cerrar cursor y conexión
            cursor.close()
            conn.close()
            return json.dumps({"status": "success", "result": result})
        except pyodbc.Error as err:
            return json.dumps({"status": "error", "message": "No hubo resultados"})
    
    #GENERA EL DATA DE LA TABLA EMPRESAS QUE SE USA EN LA FUNCION
    def get_empresas(self):
        query = "SELECT idEmpresa, NombreEmpresa FROM Empresas"
        return json.loads(self.execute_sql_query(query)).get('result', [])

    #funcion que se manda llamar 
    def query_empresa(self, query):
        if not query:
            return json.dumps({"status": "success", "message": "hubo un query"})

        result = []
        data = self.get_empresas()
        search_term = (query.get("NombreEmpresa", "")) #Busca el nombre y tipo de reporte
        report_type = (query.get("TipoReporte", ""))
        
        if "semanal" in report_type:
            report_code = 1
        elif "diario" in report_type:
            report_code = 2

        # Si no se especifica una empresa, ejecutar un procedimiento almacenado diferente
        if not search_term:
            sql_query = f"EXEC F_ReporteOportunidadesGeneralPorSemanaYDiario {report_code}"
            result = self.execute_sql_query(sql_query)
            return json.dumps({"status": "success", "message": result}) #este resultado se envia como respuesta a la funcion

        # encontrar coincidencias aproximadas
        matches = process.extract(search_term, [entry["NombreEmpresa"] for entry in data], scorer=fuzz.token_set_ratio)
        print(matches)
        if not matches: 
            return json.dumps({"status": "error", "message": "No se encontraron resultados"}) #este resultado se envia como respuesta a la funcion
        #
        best_match = None
        for match in matches:
            if match[1] > 70:  # Umbral de similitud 
                best_match = match
                break

        if best_match: 
            print(best_match)
            for entry in data: #obtiene el id de la empresa segun el resultado del match
                if (entry["NombreEmpresa"]) == best_match[0]:
                    idempresa = entry.get("idEmpresa")
                    break

            sql_query = f"EXEC F_ReporteOportunidadesPorEmpresaIdReporte {idempresa}, {report_code}"
            result = self.execute_sql_query(sql_query)
            return json.dumps({"status": "success", "message": result}) #este resultado se envia como respuesta a la funcion
        else:
            return json.dumps({"status": "error", "message": "No se encontraron resultados"}) #este resultado se envia como respuesta a la funcion
        

if __name__ == "__main__":
    '''
        Recepción de la Solicitud (question_user):
        El modelo recibe la solicitud de entrada, que puede incluir instrucciones, preguntas o comandos. Esta entrada puede estar estructurada en lenguaje natural o ser un comando explícito que requiere ejecutar una función específica.
    '''
    question_user = input("Ingresa tu pregunta: ")
    assistant = OpenAIAssistant(question_user)
     
    answer = assistant.get_response()
    print(answer)