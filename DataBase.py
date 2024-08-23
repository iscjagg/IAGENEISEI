import pyodbc
from decimal import Decimal
from fuzzywuzzy import fuzz, process
import json
from datetime import datetime

class Database:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database

    def execute_sql_query(self, query):
        try:
        
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
    
    def normalize(self, text):
        if isinstance(text, str):
            return text.strip().lower()
        return text
    
    def get_empresas(self):
        query = "SELECT idEmpresa, NombreEmpresa FROM Empresas"
        return json.loads(self.execute_sql_query(query)).get('result', [])

    def query_empresa(self, query):
        if not query:
            return json.dumps({"status": "success", "message": "hubo un"})

        result = []
        data = self.get_empresas()
        search_term = self.normalize(query.get("NombreEmpresa", ""))
        report_type = self.normalize(query.get("TipoReporte", ""))
        
        if "semanal" in report_type:
            report_code = 1
        else:
            report_code = 2

        # Si no se especifica una empresa, ejecutar un procedimiento almacenado diferente
        if not search_term:
            sql_query = f"EXEC F_ReporteOportunidadesGeneralPorSemanaYDiario {report_code}"
            result = self.execute_sql_query(sql_query)
            return json.dumps({"status": "success", "message": result})

        # encontrar coincidencias aproximadas
        matches = process.extract(search_term, [self.normalize(entry["NombreEmpresa"]) for entry in data], scorer=fuzz.token_set_ratio)
        print(matches)
        if not matches: 
            return json.dumps({"status": "error", "message": "No se encontraron resultados"})
        #
        best_match = None
        for match in matches:
            if match[1] > 70:  # Umbral de similitud 
                best_match = match
                break

        if best_match:
            for entry in data:
                if self.normalize(entry["NombreEmpresa"]) == best_match[0]:
                    idempresa = entry.get("idEmpresa")
                    break

            sql_query = f"EXEC F_ReporteOportunidadesPorEmpresaIdReporte {idempresa}, {report_code}"
            result = self.execute_sql_query(sql_query)
            return json.dumps({"status": "success", "message": result})
        else:
            return json.dumps({"status": "error", "message": "No se encontraron resultados"})

    def get_oportinudades(self):
        query = """
                SELECT 
                s.NombreSector, o.IdOportunidad, p.Nombre as NombreProspecto, o.NombreOportunidad, 
                o.ArchivoDescripcion,
                tp.Abreviatura AS AbreviaturaTipoOportunidad ,tp.Descripcion AS DescripcionTipoOportunidad ,
                te.Abreviatura AS Entrega, te.Descripcion AS EntregaDescripcion,
                ISNULL(u.Iniciales, 'S/A') AS Iniciales,
                c.Nombre AS NombreContacto,
                CASE WHEN u.Iniciales IS NULL THEN 'Sin Asignar' ELSE u.Nombre + ' ' + u.ApellidoPaterno + ' ' + u.ApellidoMaterno END AS NombreEjecutivo,
                o.Monto,(CASE WHEN o.Probabilidad = 0 THEN '0 %' ELSE CONVERT(VARCHAR, FORMAT(o.Probabilidad, '#')+' %') END) AS Probabilidad, 
                DATEDIFF(DAY,o.FechaModificacion, GETDATE()) AS DiasSinActividad, ho.Comentario, (o.monto * (o.probabilidad /  100.0)) AS MontoNormalizado, 
                FORMAT(o.FechaRegistro, 'dd/MM/yyyy') AS FechaRegistro, 
                o.FechaRegistro AS FechaRegistroDate,
                eo.Abreviatura AS AbreviaturaEstatus, eo.Descripcion AS DescripcionEstatus,
                o.Probabilidad AS Probabilidad, o.IdEjecutivo, 
                FORMAT(CASE WHEN o.IdEstatusOportunidad in(2,3,4) THEN bo2.FechaRegistro WHEN o.IdEstatusOportunidad = 1 THEN o.FechaEstimadaCierre END, 'yyyy-MM-dd') AS FechaEstimadaCierreUpd, 
                CASE WHEN  o.IdEstatusOportunidad in(2,3,4) THEN bo2.FechaRegistro WHEN  o.IdEstatusOportunidad = 1 THEN o.FechaEstimadaCierre END AS FechaEstimadaCierre,
                (CASE WHEN bo.Probabilidad = 0 THEN '0 %' ELSE CONVERT(VARCHAR, FORMAT(bo.Probabilidad, '#')+' %') END) AS ProbabilidadOriginal, 
                DATEDIFF(DAY, o.FechaRegistro, GETDATE()) AS DiasFunnel,
                o.IdEstatusOportunidad, o.IdStage, st.Stage,  CONCAT(St.Stage, ' - ', St.Concepto) as TooltipStage,
                (select count(*) FROM HistoricoOportunidades  WHERE IdOportunidad = o.IdOportunidad) as TotalComentarios,
                (select count(*) FROM Archivos  WHERE IdOportunidad = o.IdOportunidad AND eliminado = 0) as TotalArchivos,
                o.IdTipoProyecto,
                o.IdTipoEntrega
                FROM Oportunidades o
                JOIN Prospectos p ON o.IdProspecto = p.IdProspecto
                JOIN TiposOportunidad tp ON o.IdTipoProyecto = tp.IdTipoProyecto
                LEFT JOIN ContactosProspectos c ON o.IdContactoProspecto = c.IdContactoProspecto
                LEFT JOIN TiposEntrega te ON o.IdTipoEntrega = te.IdTipoEntrega
                LEFT JOIN HistoricoOportunidades ho ON ho.IdHistoricoOportunidad = (SELECT MAX(IdHistoricoOportunidad) FROM HistoricoOportunidades WHERE IdOportunidad = o.IdOportunidad)
                LEFT JOIN Archivos a ON a.IdOportunidad = (SELECT MAX(IdArchivo) FROM Archivos WHERE IdOportunidad = o.IdOportunidad)
                LEFT JOIN Usuarios u ON o.IdEjecutivo = u.IdUsuario
                LEFT JOIN StageOportunidad st ON o.IdStage = st.Id
                JOIN EstatusOportunidad eo ON o.IdEstatusOportunidad = eo.IdEstatus
                JOIN Sectores s ON p.IdSector = s.IdSector--se añade para la columna sector
                JOIN BitacoraOportunidades bo ON bo.IdBitacoraOportunidad = (SELECT MIN(IdBitacoraOportunidad) FROM BitacoraOportunidades WHERE IdOportunidad = o.IdOportunidad)
                left join (
                    SELECT IdOportunidad, max(FechaRegistro) as FechaRegistro
                    FROM BitacoraOportunidades 
                    group by IdOportunidad) as bo2
                    on bo2.IdOportunidad = o.IdOportunidad
                """
        return json.loads(self.execute_sql_query(query)).get('result', [])

    def query_oportinudades(self, query):
        result = []
        data = self.get_oportinudades()
        # Normalizar términos de búsqueda
        search_terms = {
            "NombreSector": self.normalize(query.get("NombreSector", "")),
            "NombreProyecto": self.normalize(query.get("NombreProyecto", "")),
            "NombreOportunidad": self.normalize(query.get("NombreOportunidad", "")),
            "ArchivoDescripcion": self.normalize(query.get("ArchivoDescripcion", "")),
            "AbreviaturaTipoOportunidad": self.normalize(query.get("AbreviaturaTipoOportunidad", "")),
            "DescripcionTipoOportunidad": self.normalize(query.get("DescripcionTipoOportunidad", "")),
            "Entrega": self.normalize(query.get("Entrega", "")),
            "EntregaDescripcion": self.normalize(query.get("EntregaDescripcion", "")),
            "Iniciales": self.normalize(query.get("Iniciales", "")),
            "NombreContacto": self.normalize(query.get("NombreContacto", "")),
            "NombreEjecutivo": self.normalize(query.get("NombreEjecutivo", "")),
            "Probabilidad": self.normalize(query.get("Probabilidad", "")),
            "DiasSinActividad": self.normalize(query.get("DiasSinActividad", "")),
            "Comentario": self.normalize(query.get("Comentario", "")),
            "FechaRegistro": self.normalize(query.get("FechaRegistro", "")),
            "FechaRegistroDate": self.normalize(query.get("FechaRegistroDate", "")),
            "AbreviaturaEstatus": self.normalize(query.get("AbreviaturaEstatus", "")),
            "DescripcionEstatus": self.normalize(query.get("DescripcionEstatus", "")),
            "FechaEstimadaCierre": self.normalize(query.get("FechaEstimadaCierre", "")),
            "ProbabilidadOriginal": self.normalize(query.get("ProbabilidadOriginal", "")),
            "TooltipStage": self.normalize(query.get("TooltipStage", ""))
        }

        search_terms = {k: v for k, v in search_terms.items() if v} #Depurafion de term
        
        print(f"Search terms: {search_terms}")

        #encontrar coincidencias
        for key, value in search_terms.items():
            
            entries = [entry.get(key, "") for entry in data]
            
            match = process.extractOne(value, entries, scorer=fuzz.token_set_ratio)
            print(match)
            if match and match[1] > 70:  #umbral de similitud
                best_match_value = match[0]
                print(best_match_value)
                if best_match_value is None:
                    return json.dumps({"status": "error", "message": "No se encontraron resultados"})
                break
            if key is None:
                return json.dumps({"status": "error", "message": "No se encontraron resultados"})
        
        
        if best_match_value:
                sql_query = f""";WITH OportunidadesTemp AS (
                                SELECT 
                                    s.NombreSector, o.IdOportunidad, p.Nombre as NombreProspecto, o.NombreOportunidad, 
                                    o.ArchivoDescripcion,
                                    o.IdTipoProyecto AS IdTipoOpotunidad,tp.Abreviatura AS AbreviaturaTipoOportunidad ,tp.Descripcion AS DescripcionTipoOportunidad ,
                                    o.IdTipoEntrega,te.Abreviatura AS Entrega, te.Descripcion AS EntregaDescripcion,
                                    ISNULL(u.Iniciales, 'S/A') AS Iniciales,
                                    c.Nombre AS NombreContacto,
                                    CASE WHEN u.Iniciales IS NULL THEN 'Sin Asignar' ELSE u.Nombre + ' ' + u.ApellidoPaterno + ' ' + u.ApellidoMaterno END AS NombreEjecutivo,
                                    o.Monto,(CASE WHEN o.Probabilidad = 0 THEN '0 %' ELSE CONVERT(VARCHAR, FORMAT(o.Probabilidad, '#')+' %') END) AS Probabilidad, 
                                    DATEDIFF(DAY,o.FechaModificacion, GETDATE()) AS DiasSinActividad, ho.Comentario, (o.monto * (o.probabilidad /  100.0)) AS MontoNormalizado, 
                                    FORMAT(o.FechaRegistro, 'dd/MM/yyyy') AS FechaRegistro, 
                                    o.FechaRegistro AS FechaRegistroDate,
                                    o.IdEstatusOportunidad, eo.Abreviatura AS AbreviaturaEstatus, eo.Descripcion AS DescripcionEstatus,
                                    o.Probabilidad AS desProbabilidad, o.IdEjecutivo, 
                                    FORMAT(CASE WHEN o.IdEstatusOportunidad in(2,3,4) THEN bo2.FechaRegistro WHEN o.IdEstatusOportunidad = 1 THEN o.FechaEstimadaCierre END, 'yyyy-MM-dd') AS FechaEstimadaCierreUpd, 
                                    CASE WHEN  o.IdEstatusOportunidad in(2,3,4) THEN bo2.FechaRegistro WHEN  o.IdEstatusOportunidad = 1 THEN o.FechaEstimadaCierre END AS FechaEstimadaCierre,
                                    (CASE WHEN bo.Probabilidad = 0 THEN '0 %' ELSE CONVERT(VARCHAR, FORMAT(bo.Probabilidad, '#')+' %') END) AS ProbabilidadOriginal, 
                                    DATEDIFF(DAY, o.FechaRegistro, GETDATE()) AS DiasFunnel,
                                    o.IdStage, st.Stage,  CONCAT(St.Stage, ' - ', St.Concepto) as TooltipStage,
                                    (select count(*) FROM HistoricoOportunidades  WHERE IdOportunidad = o.IdOportunidad) as TotalComentarios,
                                    (select count(*) FROM Archivos  WHERE IdOportunidad = o.IdOportunidad AND eliminado = 0) as TotalArchivos
                                    FROM Oportunidades o
                                    JOIN Prospectos p ON o.IdProspecto = p.IdProspecto
                                    JOIN TiposOportunidad tp ON o.IdTipoProyecto = tp.IdTipoProyecto
                                    LEFT JOIN ContactosProspectos c ON o.IdContactoProspecto = c.IdContactoProspecto
                                    LEFT JOIN TiposEntrega te ON o.IdTipoEntrega = te.IdTipoEntrega
                                    LEFT JOIN HistoricoOportunidades ho ON ho.IdHistoricoOportunidad = (SELECT MAX(IdHistoricoOportunidad) FROM HistoricoOportunidades WHERE IdOportunidad = o.IdOportunidad)
                                    LEFT JOIN Archivos a ON a.IdOportunidad = (SELECT MAX(IdArchivo) FROM Archivos WHERE IdOportunidad = o.IdOportunidad)
                                    LEFT JOIN Usuarios u ON o.IdEjecutivo = u.IdUsuario
                                    LEFT JOIN StageOportunidad st ON o.IdStage = st.Id
                                    JOIN EstatusOportunidad eo ON o.IdEstatusOportunidad = eo.IdEstatus
                                    JOIN Sectores s ON p.IdSector = s.IdSector--se añade para la columna sector
                                    JOIN BitacoraOportunidades bo ON bo.IdBitacoraOportunidad = (SELECT MIN(IdBitacoraOportunidad) FROM BitacoraOportunidades WHERE IdOportunidad = o.IdOportunidad)
                                    left join (
                                        SELECT IdOportunidad, max(FechaRegistro) as FechaRegistro
                                        FROM BitacoraOportunidades 
                                        group by IdOportunidad) as bo2
                                        on bo2.IdOportunidad = o.IdOportunidad
                                )
                                SELECT * FROM OportunidadesTemp WHERE {key}='{best_match_value}'
                                """
                result = self.execute_sql_query(sql_query)
                #print(result)
                return json.dumps({"status": "success", "message": result})
        else:
            return json.dumps({"status": "error", "message": "No se encontraron resultados"})    

