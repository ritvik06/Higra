############################################################################
# Copyright ESIEE Paris (2018)                                             #
#                                                                          #
# Contributor(s) : Benjamin Perret                                         #
#                                                                          #
# Distributed under the terms of the CECILL-B License.                     #
#                                                                          #
# The full license is in the file LICENSE, distributed with this software. #
############################################################################

set(PY_FILES
        __init__.py
        test_binary_partition_tree.py
        test_constrained_connectivity_hierarchy.py
        test_component_tree.py
        test_hierarchy_core.py
        test_random_hierarchy.py
        test_watershed_hierarchy.py)

REGISTER_PYTHON_MODULE_FILES("${PY_FILES}")
