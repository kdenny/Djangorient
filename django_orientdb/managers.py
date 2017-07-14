from client import *
from model_properties import all_types

import json

class DjangorientBaseManager(object):
    """
    Base class for an Edge/Node 'objects' manager
    """

    def __init__(self, cls):
        self._cls = cls
        self._class_name = self._cls.__name__

    def all(self):
        """
        Return all class documents
        """
        return client.get_all(self._class_name)

    def filter(self, **kwargs):
        """
        Get documents of a class that match the filters.
        """
        class_properties = self._get_properties()
        filter_items = dict()

        for key, val in kwargs.iteritems():
            # TODO - In the future we'll add filters that aren't a part of
            # the class properties.
            # I.E - greater_than/lesser_than properties, between dates etc
            if key not in class_properties and key != 'id':
                raise Exception("The property {property} is not a part of the class {cls}".format(property=key,
                                                                                                  cls=self._class_name))
            else:
                if key == 'id':
                    key = '@rid'
                filter_items[key] = val

        return client.filter_func(self._class_name, filter_items)

    def get_by_id(self, id):
        """
        Get a class by an id (ID has to match OrientDB ID format, I.E - '#12:2')
        """
        r = self.filter(id=id)
        if r.results:
            return r[0]

    def _get_properties(self):
        """
        Return all the properties defined by the user in the class
        (Will be used by subclasses that inherit DjangorientNode)
        """
        properties = dict()
        cls = self._cls

        for key, val in cls.__dict__.iteritems():
            if filter(lambda x: x is type(val), all_types):
                properties[key] = val
        return properties

    def _get_property_value(self, property_value, property_type):
        """
        Validate the property value with its selected type, and try to convert if incompatible
        """
        try:
            val = property_type.validate_type(property_value, try_converting=True)
        except Exception, e:
            raise e

        return val


class DjangorientNodeManager(DjangorientBaseManager):
    """
    Manager for OrientDB Nodes (vertices)
    """

    def __init__(self, cls):
        super(DjangorientNodeManager, self).__init__(cls)

    def create(self, **kwargs):
        """
        Create a document in the database, based on a certain class.
        """
        class_properties = self._get_properties()
        property_values = dict()

        for key, val in kwargs.iteritems():
            if key not in class_properties:
                raise Exception("The property {property} is not a part of the class {cls}".format(property=key,
                                                                                                  cls=self._class_name))
            else:
                property_values[key] = self._get_property_value(val, class_properties[key])

        return client.add_to_class(self._class_name, property_values)[0]


class DjangorientEdgeManager(DjangorientBaseManager):
    """
    Manager for OrientDB Edges
    """

    def __init__(self, cls):
        super(DjangorientEdgeManager, self).__init__(cls)

    def create(self, in_node, out_node, **kwargs):
        """
        Create an edge from the incoming node to the outcoming node
        """

        class_properties = self._get_properties()
        property_values = dict()

        for node in [in_node, out_node]:
            if not self._validate_node(node):
                raise Exception("{n} cannot be connected by edges...".format(n=str(node)))

        for key, val in kwargs.iteritems():
            if key not in class_properties:
                raise Exception("The property {property} is not a part of the class {cls}".format(property=key,
                                                                                                  cls=self._class_name))
            else:
                property_values[key] = self._get_property_value(val, class_properties[key])

        return client.add_edge(self._class_name, in_node.id, out_node.id, property_values)[0]

    def _validate_node(self, node):
        """
        Validate whether the node has vertex attributes & can be connected via an edge
        """
        return hasattr(node, 'id') and hasattr(node, 'class_name')




# The maximum number of items to display in a ResultSet.__repr__
REPR_OUTPUT_SIZE = 10

# Map between orient node/edge properties that are invalid/uncomprehendable
ORIENT_PROPERTIES_MAPPER = {'in': 'in_vertex',
                            'out': 'out_vertex'}

EXTERNAL_OBJECT_PROPERTIES = ['in', 'in_vertex', 'out',
                              'out_vertex']  # Properties that represent an external object & require us to query the object


class DjangorientResultSet(object):
    """
    Results returned from a query
    """

    def __init__(self, resp, content, uri=None):
        self._resp = resp
        self._content = content
        self._uri = uri
        self._check_resp()
        self.results = self._parse_resp_content()

    def __repr__(self):
        data = [cls for cls in self.results[:REPR_OUTPUT_SIZE + 1]]
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)

    def __getitem__(self, index):
        return self.results[index]

    # TODO - Fix the "client out of scope" bug, and find a way to replace the id with the actual object
    def _get_ext_object_by_id(self, obj_id):
        """
        Get the object of the given ID from the DB
        """

    # return client.get_by_id(obj_id)
    # return self

    def _build_results_list(self, initial_results_list):
        """
        Return a list of "types" representing the objects returned from the query
        """
        results = []

        for r in initial_results_list:
            values_dict = dict()

            if '@rid' in r:
                values_dict['id'] = str(r['@rid'])

            if '@class' in r:
                values_dict['class_name'] = str(r['@class'])

            for key, val in r.iteritems():
                if not key.startswith('@'):
                    property_name = ORIENT_PROPERTIES_MAPPER.get(key, key)
                    values_dict[property_name] = val

                    # TODO - Make this work...
                    # Replace ID with the actual object
                    # if property_name in EXTERNAL_OBJECT_PROPERTIES:
                    # 	values_dict[property_name] = self._get_ext_object_by_id(val)

            # Only add classes that were queried to the results
            if 'class_name' in values_dict:
                results.append(type(values_dict['class_name'], (), values_dict))

        return results

    def _parse_resp_content(self):
        """
        Parse query results into the results generator
        """
        resp_dict = self._get_results_dict()

        try:
            results_list = resp_dict['result']
        except KeyError:
            return None
        except TypeError:  # Raised when results_dict is empty
            return None

        results = self._build_results_list(results_list)
        return results

    def raw_json_resp(self):
        """
        JSON formatted representation of the query results
        """
        return str(self._content)

    def _get_results_dict(self):
        """
        Query results in a Python dictionary
        """
        try:
            if self._content:
                return json.loads(str(self._content))
        except ValueError, e:
            error_msg = "There seems to be an error... The response we received is - \n" + str(self._content)
            raise Exception(error_msg)

    def _check_resp(self):
        if self._resp['status'] == '401':
            raise Exception('Not authorized! Please enter a valid username & pw')