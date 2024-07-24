import json
import yaml
import inflect
from neo4j import GraphDatabase

URI = "bolt://neo4j:7687/"

class GraphGenerator():
    def __init__(self, openapi_file):
        ''' Init Function '''
        # Create Inflect Object for singular/plural words
        self.p = inflect.engine()

        # Import json or yaml file
        if openapi_file[-4:] == "json":
            with open(openapi_file, "r") as file:
                spec_data = json.load(file)
        elif openapi_file[-4:] == "yaml":
            with open(openapi_file, "r") as file:
                spec_data = yaml.safe_load(file)

        # Connect to neo4j GraphDatabase 
        self.driver = GraphDatabase.driver(URI)
        self.database = "neo4j"
        self.driver.verify_connectivity()
        # Reset/clear database
        self.driver.execute_query(
            "MATCH (n) DETACH DELETE n",
            database_=self.database
        )

        # Add OpenAPIFile Node to database
        self.driver.execute_query(
            "CREATE (:OpenAPIFile {name: $name, version: $version, openapi_version: $openapi_version})", 
            name=spec_data["info"]["title"],
            version=spec_data["info"]["version"],
            openapi_version=spec_data["openapi"],
            database_=self.database
        )

        # Save schemas and paths in class variables
        self.schemas = self.__get_nested_value(spec_data, ["components", "schemas"], {})
        self.paths = self.__get_nested_value(spec_data, ["paths"], {})
   
    def __get_nested_value(self, dictionary, keys, default):
        ''' Private Function to get a nested value from a dictionary '''
        current = dictionary
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def create_graph(self):
        ''' Public Function to create the Object Endpoint Dependency Graph '''
        # Add all Objects nodes to database
        for object_name in self.schemas.keys():
            self.driver.execute_query(
                "CREATE (:Object {name: $name})",
                name=object_name,
                database_=self.database
            )

        # Add property coonections to new created Property Nodes or Object Nodes
        for object_name, object_details in self.schemas.items():
            properties = self.__get_nested_value(object_details, ["properties"], {})
            for property_name, property_details in properties.items():
                # If ref exists create connection to Object Node
                ref = self.__get_nested_value(property_details, ["$ref"], "")
                if ref.startswith("#/components/schemas/"):
                    ref_object_name = ref[21:]
                    self.driver.execute_query("""
                        MATCH (o1:Object {name: $o1_name})
                        MATCH (o2:Object {name: $o2_name})
                        CREATE (o1)-[:HAS_PROPERTY {name: $p_name, list: False}]->(o2)
                        """,
                        o1_name=object_name,
                        o2_name=ref_object_name,
                        p_name=property_name,
                        database_=self.database
                    )
                    continue
                # If items-ref exists create connection to Object Node
                items_ref = self.__get_nested_value(property_details, ["items", "$ref"], "")
                if items_ref.startswith("#/components/schemas/"):
                    items_ref_object_name = items_ref[21:]
                    self.driver.execute_query("""
                        MATCH (o1:Object {name: $o1_name})
                        MATCH (o2:Object {name: $o2_name})
                        CREATE (o1)-[:HAS_PROPERTY {name: $p_name, list: True}]->(o2)
                        """,
                        o1_name=object_name,
                        o2_name=items_ref_object_name,
                        p_name=property_name,
                        database_=self.database
                    )

        # Add all Endpoint Nodes with connections to Object Nodes
        for path, operations in self.paths.items():
            for operation_name, operation_details in operations.items():
                # Get dict with requestBody, parameters and responses and each related Objects from a endpoint
                objects_from_endpoint = self.__get_objects_form_endpoint(path, operation_details)

                # Add Endpoint Node to database
                self.driver.execute_query(
                    "CREATE (:Endpoint {name: $name, path: $path, operation: $operation})",
                    name=f'{path}, {operation_name}',
                    path=path,
                    operation=operation_name,
                    database_=self.database
                )

                # Add all connections between Endpoint Node and Object Nodes
                # First connections from Request_Body
                for object in objects_from_endpoint["request_body"]:
                    self.driver.execute_query("""
                        MATCH (e:Endpoint {name: $e_name})
                        MATCH (o:Object {name: $o_name})
                        CREATE (o)-[:IN_REQUEST_BODY]->(e)
                        """,
                        e_name=f'{path}, {operation_name}',
                        o_name=object,
                        database_=self.database
                    )
                # Second connections from parameters
                for parameter, parameter_details in objects_from_endpoint["parameters"].items():
                    self.driver.execute_query("""
                        MATCH (e:Endpoint {name: $e_name})
                        MATCH (o:Object {name: $o_name})
                        CREATE (o)-[:IS_PARAMETER {parameter_name: $parameter_name, property_name: $property_name}]->(e)
                        """,
                        e_name=f'{path}, {operation_name}',
                        o_name=parameter_details["object"],
                        parameter_name=parameter,
                        property_name=parameter_details["property"],
                        database_=self.database
                    )
                # Last connections from responses
                for response, response_details in objects_from_endpoint["responses"].items():
                    for object in response_details:
                        self.driver.execute_query("""
                            MATCH (e:Endpoint {name: $e_name})
                            MATCH (o:Object {name: $o_name})
                            CREATE (e)-[:IN_RESPONSE_BODY {status_code: $status_code}]->(o)
                            """,
                            e_name=f'{path}, {operation_name}',
                            o_name=object,
                            status_code=response,
                            database_=self.database
                        )

        # Close neo4j driver connection
        self.driver.close()

    def __get_objects_form_endpoint(self, path, operation_details):
        ''' Private Function to get all related Objects from a endpoint. Returns dict with results '''
        print(path) # - Debug Info

        # Create empty dict endpoint
        endpoint = {
            'request_body': [],
            'parameters': {},
            'responses': {}
        }

        # First get related Objects from requestBody
        requestBody_content = self.__get_nested_value(operation_details, ["requestBody", "content"], {})
        if requestBody_content:
            # Filter the Object from the content
            endpoint['request_body'] = self.__objects_from_content(requestBody_content)

        # Second get related Object to all parameters 
        parameters = self.__get_nested_value(operation_details, ['parameters'], {})
        if parameters:
            # Search for potential Object
            potential_schema = self.__get_potential_object(path)
            for parameter in parameters:
                endpoint['parameters'][parameter["name"]] = self.__objects_from_parameter(parameter, potential_schema)

        # Last get related Objects to all responses
        responses = self.__get_nested_value(operation_details, ['responses'], {})
        if responses:
            for http_status, response_details in responses.items():
                response_content = self.__get_nested_value(response_details, ["content"], {})
                if response_content:
                    endpoint['responses'][http_status] = self.__objects_from_content(response_content)

        return endpoint

    def __objects_from_content(self, content):
        ''' Private Function to get Objects from content. Returns a list of names from Objects '''
        # Create empty list of Objects
        related_objects = []

        # Iterate through all media_types with its details and search for refs
        for media_type, details in content.items():
            # First check if a schema ref exists
            ref = self.__get_nested_value(details, ["schema", "$ref"], "")
            if ref.startswith("#/components/schemas/"):
                ref_object_name = ref[21:]
                if ref_object_name not in related_objects:
                        related_objects.append(ref_object_name)

            # Second check if a schema items ref exists
            items_ref = self.__get_nested_value(details, ["schema", "items", "$ref"], "")
            if items_ref.startswith("#/components/schemas/"):
                items_ref_object_name = items_ref[21:]
                if items_ref_object_name not in related_objects:
                        related_objects.append(items_ref_object_name)

        return related_objects

    def __get_potential_object(self, path):
        ''' Private Function to get a potential Object for a path name. Return this Obejct as schema'''
        potential_object = {}
        splitted_path = path[1:].split("/")

        # Iterate through the path with all comination on words and search if a schema with this name exists
        for count, path_word in enumerate(splitted_path):
            for i in range(count, len(splitted_path)+1):
                word = ''.join(splitted_path[count: i+1])
                # Checks if a schema name with this word in lower cases or in singular exists
                for schema_name, schema_infos in self.schemas.items():
                    if word.lower() == schema_name.lower():
                        potential_object = {
                            "schema": schema_name,
                            "schema_details": schema_infos
                        }
                        break
                    if word != '' and self.p.singular_noun(word) and self.p.singular_noun(word.lower()) == schema_name.lower(): # Returns False when a singular word is passed
                        potential_object = {
                            "schema": schema_name,
                            "schema_details": schema_infos
                        }
                        break

        return potential_object

    def __objects_from_parameter(self, parameter, potential_object):
        ''' Private Function to check if the potential Object fits to parameter'''
        # If no potential Object exists return ""
        if not potential_object:
            return {
                "object": "",
                "property": ""
            }
        
        if parameter["in"] == "path" or parameter["in"] == "query":
            # Iterate through all propertys from the potential_object
            for property_name, property_details in self.__get_nested_value(potential_object["schema_details"], ["properties"], {}).items():
                # Check if name and type are the same
                if property_name == parameter["name"] and self.__get_nested_value(property_details, ['type'], "") == parameter["schema"]["type"]:
                    # Check if the property from the potential Object has an ref
                    ref = self.__get_nested_value(property_details, ["$ref"], "")
                    if ref.startswith("#/components/schemas/"):
                        ref_object_name = items_ref[21:]
                        return {
                            "object": ref_object_name,
                            "property": ""
                        }
                    
                    # Check if the property from the potential Object has an items ref
                    items_ref = self.__get_nested_value(property_details, ["items", "$ref"], "")
                    if items_ref.startswith("#/components/schemas/"):
                        items_ref_object_name = items_ref[21:]
                        return {
                            "object": items_ref_object_name,
                            "property": ""
                        }
                    
                    # Else return potential Object
                    return {
                        "object": potential_object["schema"],
                        "property": ""
                    }
                            
            # IDs
            if "id" in parameter["name"].lower():
                for schema in self.schemas.keys():
                    if schema.lower() in parameter["name"]:
                        return {
                            "object": schema,
                            "property": 'id'
                        }

        # If no property from the potential object fits to the parameter return ""               
        return {
            "object": "",
            "property": ""
        }