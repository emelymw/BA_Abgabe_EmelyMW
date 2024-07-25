from neo4j import GraphDatabase
from itertools import permutations
import math

URI = "bolt://neo4j:7687/"

class SequenceGenerator():
    def __init__(self):
        ''' Init Function '''
        # Connect to neo4j GraphDatabase 
        self.driver = GraphDatabase.driver(URI)
        self.database = "neo4j"
        self.driver.verify_connectivity()

        # Init class variables 
        self.object_crud = None
        self.object_list = None
        self.endpoint_list = None
        
    def get_infos(self):
        ''' Function to get all generic informations about the API and generate the testing templates '''
        # Get informations from OpenAPIFile Node from datebase
        records, summary, keys = self.driver.execute_query(
            "MATCH (f:OpenAPIFile) RETURN f"
        )
        
        # Call private functions which create and return the testing templates
        self.object_list = self.__set_object_list()
        self.object_crud = self.__set_object_crud()
        self.endpoint_list = self.__set_endpoint_list()

        # Close neo4j driver connection
        self.driver.close()

        # Return generic informations about API
        return {
            'name': records[0].data()['f']['name'],
            'version': records[0].data()['f']['version'],
            'openapi_version': records[0].data()['f']['openapi_version'],
        }
        
    def get_object_list(self):
        ''' Get function for object_list dictionary'''
        return self.object_list
    
    def get_object_crud(self):
        ''' Get function for object_crud dictionary '''
        return self.object_crud
    
    def get_endpoint_list(self):
        ''' Get function for endpoint_list dictionary '''
        return self.endpoint_list

    def __set_object_list(self):
        ''' Private function to set the object_list dictionary '''
        # Get informations from all Object Nodes from database
        all_objects, summary, keys = self.driver.execute_query(
            "MATCH (o:Object) RETURN o",
        )
        # Get informations from all Endpoint Nodes from database
        all_endpoints, summary, keys = self.driver.execute_query(
            "MATCH (e:Endpoint) RETURN e",
        )

        # Init result variable 
        result = {}
        # Init variable which stores all endpoints that have been used from at leatst one object
        finished_endpoints_all = []
        # Iterate through all objects and search for all endpoints where are directly used
        for object in all_objects:
            # Get all related Endpoint Nodes with informations about the relationship
            endpoints, summary, keys = self.driver.execute_query(
                "MATCH (e:Endpoint)-[r]-(o:Object {name: $name}) RETURN e, r, PROPERTIES(r)",
                name=object.data()['o']['name']
            )
            # Init object name as key in result
            result[object.data()['o']['name']] = {}
            # Iterate through all endpoints with relationship which are found
            for endpoint in endpoints:
                # Check if the endpoint is already in the dictionary from this object
                if endpoint.data()['e']['name'] not in result[object.data()['o']['name']].keys():
                    result[object.data()['o']['name']][endpoint.data()['e']['name']] = []

                # if the relationship is from request-body save only the name
                if endpoint.data()['r'][1] == "IN_REQUEST_BODY":
                    info = f'{endpoint.data().get("r")[1]}'
                # if the relationship is from response-body save the name and the status code
                elif endpoint.data()['r'][1] == "IN_RESPONSE_BODY":
                    info = f'{endpoint.data()['r'][1]} - {endpoint.data()['PROPERTIES(r)']['status_code']}'
                    # if the relationship is from a parameter save the name and the parameter namen and if not equal the property name too
                elif endpoint.data()['r'][1] == "IS_PARAMETER":
                    info = f'{endpoint.data()['r'][1]} - {endpoint.data()['PROPERTIES(r)']['parameter_name']} - {endpoint.data()['PROPERTIES(r)']['property_name']}'
                
                # add info to list
                result[object.data()['o']['name']][endpoint.data()['e']['name']].append(info)
                # add endpoint name to finished endpoints list
                finished_endpoints_all.append(endpoint.data()['e']['name'])

        # Save all Endpoints which are never used one time in this list
        result["NO_OBJECT"] = []
        for endpoint in all_endpoints:
            if endpoint.data()['e']['name'] not in finished_endpoints_all and endpoint.data()['e']['name'] not in result['NO_OBJECT']:
                result["NO_OBJECT"].append(endpoint.data()['e']['name'])

        return result
    
    def __set_object_crud(self):
        ''' Private function to set the object_crud dictionary '''
        # Get informations from all Object Nodes from database
        objects, summary, keys = self.driver.execute_query(
            "MATCH (o:Object) RETURN o",
        )

        # Get informations from all Endpoint Nodes from database
        all_endpoints, summary, keys = self.driver.execute_query(
            "MATCH (e:Endpoint) RETURN e",
        )

        # Init result variable 
        result = {}
        # Init variable which stores all endpoints that have been used from at leatst one object
        finished_endpoints_all = []
        for object in objects:
            # Get all related Endpoints Nodes
            endpoints, summary, keys = self.driver.execute_query(
                "MATCH (e:Endpoint)-[r]-(o:Object {name: $name}) RETURN DISTINCT e, r",
                name=object.data()['o']['name']
            )
            # Init object name as key in result
            result[object.data()['o']['name']] = {
                "create": [],
                "read": [],
                "update": [],
                "delete": []
            }
            # Init variable to save finsihed endpoints, so that each endpoint can only assigned once for each object 
            finished_endpoints = []
            for endpoint in endpoints:
                if endpoint.data()['e']['name'] not in finished_endpoints:
                    # Check if the endpoint is da create, read, update or delete endpoint from this object, if yes append it in list
                    if endpoint.data()['e']['operation'] == "post" and (endpoint.data()['r'][1] == "IN_REQUEST_BODY" or endpoint.data()['r'][1] == "IS_PARAMETER"):
                        result[object.data()['o']['name']]["create"].append(endpoint.data()['e']['name'])
                        finished_endpoints.append(endpoint.data()['e']['name'])
                    elif endpoint.data()['e']['operation'] == "get" and endpoint.data()['r'][1] == "IN_RESPONSE_BODY":
                        result[object.data()['o']['name']]["read"].append(endpoint.data()['e']['name'])
                        finished_endpoints.append(endpoint.data()['e']['name'])
                    elif endpoint.data()['e']['operation'] == "put" or endpoint.data()['e']['operation'] == "patch":
                        result[object.data()['o']['name']]["update"].append(endpoint.data()['e']['name'])
                        finished_endpoints.append(endpoint.data()['e']['name'])
                    elif endpoint.data()['e']['operation'] == "delete":
                        result[object.data()['o']['name']]["delete"].append(endpoint.data()['e']['name'])
                        finished_endpoints.append(endpoint.data()['e']['name'])
            finished_endpoints_all.extend(finished_endpoints)

        # Save all Endpoints which are never used one time in this list
        result["NO_OBJECT"] = []
        for endpoint in all_endpoints:
            if endpoint.data()['e']['name'] not in finished_endpoints_all:
                result["NO_OBJECT"].append(endpoint.data()['e']['name'])

        return result
    
    def __set_endpoint_list(self):
        ''' Private function to set the endpoint_list dictionary '''
        # Get informations from all Object Nodes from database
        all_endpoints, summary, keys = self.driver.execute_query(
            "MATCH (e:Endpoint) RETURN e",
        )

        # Init result variable 
        result = {}
        # Iterate through all endpoints and create preparation and dismantling sequences, get list of alle connected objects and sequence_length for testing this endpoint
        for endpoint in all_endpoints:
            # Init cariables
            connected_with_objects = []
            preparation = []
            dismantling = []
            sequence_length = 0

            # Check if the endpoint is create or delete endpoint from a object
            crud_endpoint = None
            for object_name, crud_details in self.object_crud.items():
                if object_name != "NO_OBJECT" and endpoint.data()['e']['name'] in crud_details['create']:
                    crud_endpoint = (object_name, "create")
                    break
                if object_name != "NO_OBJECT" and endpoint.data()['e']['name'] in crud_details['delete']:
                    crud_endpoint = (object_name, "delete")
                    break
                
            
            # Get all related Object Nodes with informations about the relationship
            relationship_objects, summary, keys = self.driver.execute_query(
                "MATCH (e:Endpoint {name: $name})-[r]-(o:Object) RETURN o, r", 
                name=endpoint.data()['e']['name']
            )
            
            # Get all paths from graph with HAS_PROPERTY relationship beetween Objects
            paths = []
            for relationship_object in relationship_objects:
                if relationship_object.data()['o']['name'] not in connected_with_objects:
                    connected_with_objects.append(relationship_object.data()['o']['name'])
                    property_objects, summary, keys = self.driver.execute_query(
                            """MATCH (start :Object {name: $name})
                            CALL {
                                WITH start
                                MATCH path = (start)-[:HAS_PROPERTY*]->(end)
                                WHERE NOT (end)-[:HAS_PROPERTY]->()
                                RETURN path
                            }
                                RETURN [n IN nodes(path) | n.name] AS nodeSequence
                                ORDER BY size(nodes(path)) DESC
                            """,
                            name=relationship_object.data()['o']['name']
                        )
                    
                    if property_objects:
                        for property_object in property_objects:
                            paths.append(property_object['nodeSequence'][::-1])
                            for object_name in property_object['nodeSequence']:
                                if object_name not in connected_with_objects:
                                    connected_with_objects.append(object_name)
                    else:
                        paths.append([relationship_object.data()['o']['name']])

            # Get alle dependency tupels from paths
            dependencies = []
            for path in paths:
                for count, object in enumerate(path):
                    if count != len(path)-1 and (path[count], path[count+1]) not in dependencies:
                        dependency = (path[count], path[count+1])
                        dependencies.append(dependency)

            # Create all permutations from objects and check if there fit all deoendency
            perm = permutations(connected_with_objects)
            paths = []
            for i in list(perm):
                check = True
                for dependency in dependencies:
                    if i.index(dependency[0]) > i.index(dependency[1]):
                        check = False
                if check:
                    paths.append(i)

            # Iterate through all valid object paths and create sequences
            for path in paths:
                endpoint_list_preparation = []
                endpoint_list_dismantling = []
                for object in path:
                    count = len(endpoint_list_preparation)
                    # preparation
                    if crud_endpoint == None or crud_endpoint[1] == "delete" or crud_endpoint[0] != object:
                        if self.object_crud[object]["create"]:
                            if count == 0:
                                for create_method in self.object_crud[object]["create"]:
                                    endpoint_list_preparation.append([create_method])
                            else:
                                new_pre_lists = []
                                for pre_list in endpoint_list_preparation:
                                    copy_pre_list = pre_list.copy()
                                    
                                    for index, create_method in enumerate(self.object_crud[object]["create"]):
                                        if index == 0:
                                            pre_list.append(create_method)
                                        else:
                                            copy_copy_pre_list = copy_pre_list.copy()
                                            copy_copy_pre_list.append(create_method)
                                            new_pre_lists.append(copy_copy_pre_list)
                                endpoint_list_preparation = endpoint_list_preparation + new_pre_lists
                        else:
                            if count == 0:
                                endpoint_list_preparation.append([f'Placeholder<{object}>'])
                            else:
                                for pre_list in endpoint_list_preparation:
                                    pre_list.append(f'Placeholder<{object}>')
                    # dismantling
                    if crud_endpoint == None or crud_endpoint[1] == "create" or crud_endpoint[0] != object:
                        if self.object_crud[object]["delete"]:
                            if count == 0:
                                for delete_method in self.object_crud[object]["delete"]:
                                    endpoint_list_dismantling.append([delete_method])
                            else:
                                new_dis_lists = []
                                for dis_list in endpoint_list_dismantling:
                                    copy_dis_list = dis_list.copy()
                                    
                                    for index, delete_method in enumerate(self.object_crud[object]["delete"]):
                                        if index == 0:
                                            dis_list.append(delete_method)
                                        else:
                                            copy_copy_dis_list = copy_dis_list.copy()
                                            copy_copy_dis_list.append(delete_method)
                                            new_dis_lists.append(copy_copy_dis_list)
                                endpoint_list_dismantling = endpoint_list_dismantling + new_dis_lists
                        else:
                            if count == 0:
                                endpoint_list_dismantling.append([f'Placeholder<{object}>'])
                            else:
                                for dis_list in endpoint_list_dismantling:
                                    dis_list.append(f'Placeholder<{object}>')

                preparation = preparation + endpoint_list_preparation
                dismantling = dismantling + endpoint_list_dismantling

            # Calculate sequence_length
            if preparation:
                sequence_length = sequence_length + self.average_sequnece_lenght(preparation)
            if dismantling:
                sequence_length = sequence_length + self.average_sequnece_lenght(dismantling)
            result[endpoint.data()['e']['name']] = {
                "connected_with_objects": connected_with_objects,
                "preparation": preparation,
                "dismantling": dismantling,
                "sequence_length": sequence_length
            }
            print(f"{endpoint.data()['e']['name']} - {sequence_length}")

        return result
    
    def average_sequnece_lenght(self, list):
        ''' Function, to get the average lenght of lists in a list '''
        count_lists = len(list)
        count_sequnces = sum(len(sub_list) for sub_list in list)
        average_lenght = count_sequnces / count_lists if count_lists > 0 else 0
        return math.ceil(average_lenght)

    def close_driver(self):
        self.driver.close()