#############################
# ontology_explorer.py
#############################


# import needed libraries
import glob
import pickle

from datetime import datetime
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL
from tqdm import tqdm

# define global namespace
obo = Namespace('http://purl.obolibrary.org/obo/')
oboinowl = Namespace('http://www.geneontology.org/formats/oboInOwl#')


class OntologyEx(object):
    """Class creates an RDF graph from an OWL file and then performs queries to return DbXRefs, synonyms, and labels.

    Attributes:
        graph: An rdflib graph object.
    """

    def __init__(self) -> None:
        self.graph: Graph = Graph()

    def get_ontology_information(self, ont_id: str, codes: list) -> dict:
        """Function queries an RDF graph and returns labels, definitions, dbXRefs, and synonyms for all
        non-deprecated ontology classes.

        Args:
            ont_id: A string containing part of an ontology ID.
            codes: A list of strings that represent terminology names.

        Returns: A dict mapping each DbXRef to a list containing the corresponding class ID and label. For example:
            {'http://purl.obolibrary.org/obo/HP_0007321': {
                'label': ['deep white matter hypodensities'],
                'definition': ['multiple areas of darker than expected signal on magnetic resonance imaging emanating
                               from the deep cerebral white matter.'],
                'dbxref': ['UMLS:C1856979'],
                'synonyms': ['deep cerebral white matter hypodensities']}
        """

        start = datetime.now()
        print('Identifying ontology information: {}'.format(start))
        res = {}

        # get classes
        class_ids = [x for x in self.graph.subjects(RDF.type, OWL.Class) if isinstance(x, URIRef)]
        class_dep = self.graph.subjects(OWL.deprecated,
                                        Literal('true',
                                                datatype=URIRef('http://www.w3.org/2001/XMLSchema#boolean')))

        for cls in tqdm(class_ids):
            if ont_id in str(cls) and cls not in list(class_dep):
                res[str(cls)] = {}

                # labels
                res[str(cls)]['label'] = [str(x).encode('ascii', 'ignore').lower().decode('utf-8')
                                          for x in list(self.graph.objects(cls, RDFS.label))]

                # definitions
                res[str(cls)]['definition'] = [str(x).encode('ascii', 'ignore').lower().decode('utf-8')
                                               for x in list(self.graph.objects(cls, URIRef(obo + 'IAO_0000115')))]

                # dbXRef
                if codes:
                    res[str(cls)]['dbxref'] = [str(x) for x in
                                               list(self.graph.objects(cls, URIRef(oboinowl + 'hasDbXref')))
                                               if any(i for i in codes if i in str(x))]
                # synonyms
                syns = [str(x).encode('ascii', 'ignore').lower().decode('utf-8')
                        for x in list(self.graph.objects(cls, URIRef(oboinowl + 'hasSynonym')))]
                syns += [str(x).encode('ascii', 'ignore').lower().decode('utf-8')
                         for x in list(self.graph.objects(cls, URIRef(oboinowl + 'hasExactSynonym')))]
                syns += [str(x).encode('ascii', 'ignore').lower().decode('utf-8')
                         for x in list(self.graph.objects(cls, URIRef(oboinowl + '#hasBroadSynonym')))]
                syns += [str(x).encode('ascii', 'ignore').lower().decode('utf-8')
                         for x in list(self.graph.objects(cls, URIRef(oboinowl + 'hasNarrowSynonym')))]
                syns += [str(x).encode('ascii', 'ignore').lower().decode('utf-8')
                         for x in list(self.graph.objects(cls, URIRef(oboinowl + 'hasRelatedSynonym')))]
                res[str(cls)]['synonyms'] = syns

        finish = datetime.now()
        print("Finished processing query: {}".format(finish))

        return res

    def ontology_info_getter(self, ont_info_dictionary: dict) -> None:
        """Using different information from the user, this function retrieves all class labels, definitions,
        synonyms, and database cross-references (dbXref). The function expects a dictionary as input where the keys are
        short nick-names or OBO abbreviations for ontologies and the values are lists, where the first item is a string
        that contains the file path information to the downloaded ontology, the second item is a list of clinical
        identifiers that can be used for filtering the dbXrefs. An example of this input is shown below.

            {'CHEBI': ['resources/ontologies/chebi_without_imports.owl', ['DrugBank', 'ChEMBL', 'UniProt']]}

        Args:
            ont_info_dictionary: A dictionary. Detail on this is provided in the function description.

        Returns:
            None.
        """

        for ont in ont_info_dictionary.items():
            print('\n****** Processing Ontology: {0}'.format(ont[0]))

            # create graph
            print('Loading RDF Graph')
            self.graph = Graph().parse(ont[1][0], format='xml')

            # get ontology information
            ont_dict = self.get_ontology_information(ont[0], ont[1][1])
            with open(str(ont[1][0][:-4]) + '_class_information.pickle', 'wb') as handle:
                pickle.dump(ont_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)

        return None

    @staticmethod
    def ontology_loader(ontologies: list) -> dict:
        """Function takes a list of file paths to pickled data, loads the data, and then saves each file as a dictionary
        entry.

        Args:
            ontologies: A list of strings representing ontologies.

        Returns:
            A dictionary where each key is a file name and each value is a dictionary.

        Raises:
            ValueError: If the provided ontology name does not match any downloaded ontology files.
            ValueError: If the number of dictionary entries does not equal the number of files in the files list.
        """

        # find files that match user input
        ont_files = [(e, glob.glob('resources/ontologies/' + str(e.lower()) + '*.pickle')[0]) for e in ontologies]

        if len(ont_files) == 0:
            raise ValueError('Unable to find files that include that ontology name')
        else:
            ontology_data = {}
            for ont, f in tqdm(ont_files):
                with open(f, 'rb') as _file:
                    ontology_data[ont] = pickle.load(_file)

            if len(ont_files) != len(ontology_data):
                raise ValueError('Unable to load all of files referenced in the file path')
            else:
                return ontology_data
