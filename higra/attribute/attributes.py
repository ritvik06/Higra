############################################################################
# Copyright ESIEE Paris (2018)                                             #
#                                                                          #
# Contributor(s) : Benjamin Perret                                         #
#                                                                          #
# Distributed under the terms of the CECILL-B License.                     #
#                                                                          #
# The full license is in the file LICENSE, distributed with this software. #
############################################################################


import numpy as np
import higra as hg


@hg.data_provider("vertex_area")
@hg.auto_cache
def attribute_vertex_area(graph):
    """
    Vertex area of the given graph.

    In general the area of a vertex if simply equal to 1. But, if the graph is a region adjacency graph then the area of
    a region is equal to the sum of the area of the vertices inside the region (obtained with a recursive call to
    ``attribute_vertex_area`` on the original graph).

    **Provider name**: "vertex_area"

    :param graph: input graph
    :return: a 1d array
    """
    if hg.CptRegionAdjacencyGraph.validate(graph):  # this is a rag like graph
        pre_graph = hg.CptRegionAdjacencyGraph.get_pre_graph(graph)
        pre_graph_vertex_area = attribute_vertex_area(pre_graph)
        return hg.rag_accumulate_on_vertices(graph, hg.Accumulators.sum, vertex_weights=pre_graph_vertex_area)
    res = np.ones((graph.num_vertices(),), dtype=np.float64)
    res = hg.delinearize_vertex_weights(res, graph)
    return res


@hg.data_provider("edge_length")
@hg.auto_cache
def attribute_edge_length(graph):
    """
    Edge length of the given graph.

    In general the length of an edge if simply equal to 1. But, if the graph is a region adjacency graph then the
    length of an edge is equal to the sum of length of the corresponding edges in the original graph (obtained with a
    recursive call to ``attribute_edge_length`` on the original graph).

    **Provider name**: "edge_length"

    :param graph: input graph
    :return: a nd array
    """
    if hg.CptRegionAdjacencyGraph.validate(graph):  # this is a rag like graph
        pre_graph = hg.CptRegionAdjacencyGraph.get_pre_graph(graph)
        pre_graph_edge_length = attribute_edge_length(pre_graph)
        return hg.rag_accumulate_on_edges(graph, hg.Accumulators.sum, edge_weights=pre_graph_edge_length)
    res = np.ones((graph.num_edges(),), dtype=np.float64)
    return res


@hg.data_provider("vertex_perimeter")
@hg.argument_helper("edge_length")
@hg.auto_cache
def attribute_vertex_perimeter(graph, edge_length):
    """
    Vertex perimeter of the given graph.
    The perimeter of a vertex is defined as the sum of the length of out-edges of the vertex.

    If the input graph has an attribute value `no_border_vertex_out_degree`, then each vertex perimeter is assumed to be
    equal to this attribute value. This is a convenient method to handle image type graphs where an outer border has to be
    considered.

    **Provider name**: "vertex_perimeter"

    :param graph: input graph
    :param edge_length: length of the edges of the input graph (provided by :func:`~higra.attribute_edge_length` on `graph`)
    :return: a nd array
    """
    special_case_border_graph = hg.get_attribute(graph, "no_border_vertex_out_degree")

    if special_case_border_graph is not None:
        res = np.full((graph.num_vertices(),), special_case_border_graph, dtype=np.float64)
        res = hg.delinearize_vertex_weights(res, graph)
        return res

    res = hg.accumulate_graph_edges(graph, edge_length, hg.Accumulators.sum)
    res = hg.delinearize_vertex_weights(res, graph)
    return res


@hg.data_provider("vertex_coordinates")
@hg.argument_helper(hg.CptGridGraph)
@hg.auto_cache
def attribute_vertex_coordinates(graph, shape):
    """
    Coordinates of the vertices of the given grid graph.

    **Provider name**: "vertex_coordinates"

    Example
    =======

    >>> g = hg.get_4_adjacency_graph((2, 3))
    >>> c = hg.attribute_vertex_coordinates(g)
    (((0, 0), (0, 1), (0, 2)),
     ((1, 0), (1, 1), (1, 2)))

    :param graph: Input graph (Concept :class:`~higra.CptGridGraph`)
    :param shape: (deduced from :class:`~higra.CptGridGraph`)
    :return: a nd array
    """
    coords = np.meshgrid(np.arange(shape[1]), np.arange(shape[0]))
    coords = [c.reshape((-1,)) for c in coords]
    attribute = np.stack(list(reversed(coords)), axis=1)
    attribute = hg.delinearize_vertex_weights(attribute, graph)
    return attribute


@hg.data_provider("area")
@hg.argument_helper(hg.CptHierarchy, ("leaf_graph", "vertex_area"))
@hg.auto_cache
def attribute_area(tree, vertex_area=None, leaf_graph=None):
    """
    Area of each node the given tree.
    The area of a node is equal to the sum of the area of the leaves of the subtree rooted in the node.

    **Provider name**: "area"

    :param tree: input tree (Concept :class:`~higra.CptHierarchy`)
    :param vertex_area: area of the vertices of the leaf graph of the tree (provided by :func:`~higra.attribute_vertex_area` on `leaf_graph` )
    :param leaf_graph: (deduced from :class:`~higra.CptHierarchy`)
    :return: a 1d array
    """
    if vertex_area is None:
        vertex_area = np.ones((tree.num_leaves(),), dtype=np.float64)

    if leaf_graph is not None:
        vertex_area = hg.linearize_vertex_weights(vertex_area, leaf_graph)
    return hg.accumulate_sequential(tree, vertex_area, hg.Accumulators.sum)


@hg.data_provider("volume")
@hg.argument_helper("area")
@hg.auto_cache
def attribute_volume(tree, altitudes, area):
    """
    Volume of each node the given tree.
    The volume :math:`V(n)` of a node :math:`n` is defined recursively as:

    .. math::

        V(n) = area(n) * | altitude(n) - altitude(parent(n)) | +  \sum_{c \in children(n)} V(c)

    **Provider name**: "volume"

    :param tree: input tree
    :param altitudes: node altitudes of the input tree
    :param area: area of the nodes of the input hierarchy (provided by :func:`~higra.attribute_area` on `tree`)
    :return: a 1d array
    """
    height = np.abs(altitudes[tree.parents()] - altitudes)
    height = height * area
    volume_leaves = height[:tree.num_leaves()]
    return hg.accumulate_and_add_sequential(tree, height, volume_leaves, hg.Accumulators.sum)


@hg.data_provider("lca_map")
@hg.argument_helper(hg.CptHierarchy)
@hg.auto_cache
def attribute_lca_map(tree, leaf_graph):
    """
    Lowest common ancestor of `i` and `j` for each edge :math:`(i, j)` of the leaf graph of the given tree.

    Complexity: :math:`\mathcal{O}(n\log(n)) + \mathcal{O}(m)` where :math:`n` is the number of nodes in `tree` and
    :math:`m` is the number of edges in :attr:`leaf_graph`.

    **Provider name**: "lca_map"

    :param tree: input tree (Concept :class:`~higra.CptHierarchy`)
    :param leaf_graph: graph on the leaves of the input tree (deduced from :class:`~higra.CptHierarchy` on `tree`)
    :return: a 1d array
    """
    lca = hg.make_lca_fast(tree)
    res = lca.lca(leaf_graph)
    return res


@hg.data_provider("frontier_length")
@hg.argument_helper(hg.CptHierarchy, ("leaf_graph", "edge_length"))
@hg.auto_cache
def attribute_frontier_length(tree, edge_length, leaf_graph=None):
    """
    Length of the frontier represented by each node the given partition tree.

    In a partition tree, each node represent the merging of 2 or more regions.
    The frontier of a node is then defined as the common contour between the merged regions.
    This function compute the length of these common contours as the sum of the length of edges going from one of the
    merged region to the other one.

    **Provider name**: "frontier_length"

    The result has the same dtype as the edge_length array.

    :param tree: input tree
    :param edge_length: length of the edges of the leaf graph (provided by :func:`~higra.attribute_edge_length` on `leaf_graph`)
    :param leaf_graph: graph on the leaves of the input tree (deduced from :class:`~higra.CptHierarchy`)
    :return: a 1d array
    """
    lca_map = attribute_lca_map(tree, leaf_graph)

    frontier_length = np.zeros((tree.num_vertices(),), dtype=edge_length.dtype)
    np.add.at(frontier_length, lca_map, edge_length)
    return frontier_length


@hg.data_provider("frontier_strength")
@hg.argument_helper(hg.CptHierarchy)
@hg.auto_cache
def attribute_frontier_strength(tree, edge_weights, leaf_graph):
    """
    Mean edge weight along the frontier represented by each node the given partition tree.

    In a partition tree, each node represent the merging of 2 or more regions.
    The frontier of a node is then defined as the common contour between the merged regions.
    This function compute the strength of a common contour as the sum of the weights of edges going from one of the
    merged region to the other one divided by the length of the contour.

    **Provider name**: "frontier_strength"

    The result has the same dtype as the edge_weights array.

    :param tree: input tree
    :param edge_weights: weight of the edges of the leaf graph (if leaf_graph is a region adjacency graph, edge_weights might be weights on the edges of the pre-graph of the rag).
    :param leaf_graph: graph on the leaves of the input tree (deduced from :class:`~higra.CptHierarchy`)
    :return: a 1d array
    """
    # this is a rag like graph
    if hg.CptRegionAdjacencyGraph.validate(leaf_graph) and edge_weights.shape[0] != leaf_graph.num_edges():
        edge_weights = hg.rag_accumulate_on_edges(leaf_graph, hg.Accumulators.sum, edge_weights=edge_weights)

    frontier_length = hg.attribute_frontier_length(tree, leaf_graph=leaf_graph)
    frontier_strength = hg.attribute_frontier_length(tree, edge_weights, leaf_graph)
    frontier_strength[tree.num_leaves():] = frontier_strength[tree.num_leaves():] / frontier_length[tree.num_leaves():]
    return frontier_strength


@hg.data_provider("contour_length")
@hg.argument_helper(hg.CptHierarchy, ("leaf_graph", "vertex_perimeter"), ("leaf_graph", "edge_length"))
@hg.auto_cache
def attribute_contour_length(tree, vertex_perimeter, edge_length, leaf_graph=None):
    """
    Length of the contour (perimeter) of each node of the given tree.

    **Provider name**: "contour_length"

    :param tree: input tree (Concept :class:`~higra.CptHierarchy`)
    :param vertex_perimeter: perimeter of each vertex of the leaf graph (provided by :func:`~higra.attribute_vertex_perimeter` on `leaf_graph`)
    :param edge_length: length of each edge of the leaf graph (provided by :func:`~higra.attribute_edge_length` on `leaf_graph`)
    :param leaf_graph: (deduced from :class:`~higra.CptHierarchy`)
    :return: a 1d array
    """
    if leaf_graph is not None:
        vertex_perimeter = hg.linearize_vertex_weights(vertex_perimeter, leaf_graph)

    if tree.category() == hg.TreeCategory.PartitionTree:
        frontier_length = hg.attribute_frontier_length(tree, edge_length, leaf_graph)
        perimeter = hg.accumulate_and_add_sequential(tree, -2 * frontier_length, vertex_perimeter,
                                                     hg.Accumulators.sum)
    elif tree.category() == hg.TreeCategory.ComponentTree:
        perimeter = hg.cpp._attribute_contour_length_component_tree(tree, leaf_graph, vertex_perimeter,
                                                                    edge_length)

    return perimeter


@hg.data_provider("contour_strength")
@hg.argument_helper(hg.CptHierarchy, ("leaf_graph", "vertex_perimeter"), ("leaf_graph", "edge_length"))
@hg.auto_cache
def attribute_contour_strength(tree, edge_weights, vertex_perimeter, edge_length, leaf_graph=None):
    """
    Strength of the contour of each node of the given tree. The strength of the contour of a node is defined as the
    mean edge weights on the contour.

    **Provider name**: "contour_strength"

    :param tree: input tree (Concept :class:`~higra.CptHierarchy`)
    :param edge_weights: edge_weights of the leaf graph
    :param vertex_perimeter: perimeter of each vertex of the leaf graph (provided by :func:`~higra.attribute_vertex_perimeter` on `leaf_graph`)
    :param edge_length: length of each edge of the leaf graph (provided by :func:`~higra.attribute_edge_length` on `leaf_graph`)
    :param leaf_graph: (deduced from :class:`~higra.CptHierarchy`)
    :return: a 1d array
    """

    perimeter = attribute_contour_length(tree, vertex_perimeter, edge_length, leaf_graph)
    if perimeter[-1] == 0:
        perimeter[-1] = 1

    if hg.CptRegionAdjacencyGraph.validate(leaf_graph):
        edge_weights = hg.rag_accumulate_on_edges(leaf_graph, hg.Accumulators.sum, edge_weights)

    vertex_weights_sum = hg.accumulate_graph_edges(leaf_graph, edge_weights, hg.Accumulators.sum)
    edge_weights_sum = attribute_contour_length(tree, vertex_weights_sum, edge_weights, leaf_graph)

    return edge_weights_sum / perimeter


@hg.data_provider("compactness")
@hg.argument_helper("area", "contour_length")
@hg.auto_cache
def attribute_compactness(tree, area, contour_length, normalize=True):
    """
    The compactness of a node is defined as its area divided by the square of its perimeter length.

    **Provider name**: "compactness"

    :param tree: input tree
    :param area: node area of the input tree (provided by :func:`~higra.attribute_area` on `tree`)
    :param contour_length: node contour length of the input tree (provided by :func:`~higra.attribute_perimeter_length` on `tree`)
    :param normalize: if True the result is divided by the maximal compactness value in the tree
    :return: a 1d array
    """
    compactness = area / (contour_length * contour_length)
    if normalize:
        max_compactness = np.nanmax(compactness)
        compactness = compactness / max_compactness

    return compactness


@hg.data_provider("mean_weights")
@hg.argument_helper(hg.CptHierarchy, "area")
@hg.auto_cache
def attribute_mean_weights(tree, vertex_weights, area, leaf_graph=None):
    """
    Mean weight of the leaf graph vertices inside each node of the given tree.

    **Provider name**: "mean_weights"

    :param tree: input tree (Concept :class:`~higra.CptHierarchy`)
    :param vertex_weights: vertex weights of the leaf graph of the input tree
    :param area: area of the tree nodes  (provided by :func:`~higra.attribute_area` on `tree`)
    :param leaf_graph: leaf graph of the input tree (deduced from :class:`~higra.CptHierarchy`)
    :return: a nd array
    """

    if leaf_graph is not None:
        vertex_weights = hg.linearize_vertex_weights(vertex_weights, leaf_graph)

    attribute = hg.accumulate_sequential(
        tree,
        vertex_weights.astype(np.float64),
        hg.Accumulators.sum) / area.reshape((-1, 1))
    return attribute


@hg.data_provider("sibling")
@hg.auto_cache
def attribute_sibling(tree, skip=1):
    """
    Sibling index of each node of the given tree.

    For each node :math:`n` which is the :math:`k`-th child of its parent node :math:`p` among :math:`N` children,
    the attribute sibling of :math:`n` is the index of the :math:`(k + skip) % N`-th child of :math:`p`.

    The sibling of the root node is itself.

    The sibling attribute enables to easily emulates a (doubly) linked list among brothers.

    In a binary tree, the sibling attribute of a node is effectively its only brother (with `skip` equals to 1).

    **Provider name**: "sibling"

    :param tree: Input tree
    :param skip: Number of skipped element in the children list (including yourself)
    :return: a nd array
    """
    attribute = hg.cpp._attribute_sibling(tree, skip)
    return attribute


@hg.data_provider("depth")
@hg.auto_cache
def attribute_depth(tree):
    """
    The depth of a node :math:`n` of the tree :math:`T` is equal to the number of ancestors of :math:`n` in :math:`T`.

    The depth of the root node is equal to 0.

    **Provider name**: "depth"

    :param tree: Input tree
    :return: a nd array
    """
    attribute = hg.cpp._attribute_depth(tree)
    return attribute


@hg.data_provider("regular_altitudes")
@hg.argument_helper("depth")
@hg.auto_cache
def attribute_regular_altitudes(tree, depth):
    """
    Regular altitudes is comprised between 0 and 1 and is inversely proportional to the depth of a node

    **Provider name**: "regular_altitudes"

    :param tree: input tree
    :param depth: depth of the tree node (provided by :func:`~higra.attribute_depth` on `tree`)
    :return: a nd array
    """

    altitudes = 1 - depth / np.max(depth)
    altitudes[:tree.num_leaves()] = 0
    return altitudes


@hg.data_provider("vertex_list")
@hg.auto_cache
def attribute_vertex_list(tree):
    """
    List of leaf nodes inside the sub-tree rooted in a node.

    **WARNING**: This function is slow and will use O(n²) space, with n the number of leaf nodes !

    **SHOULD ONLY BE USED FOR DEBUGGING AND TESTING**

    **Provider name**: "vertex_list"

    :param tree: input tree
    :return: a list of lists
    """
    result = [[i] for i in tree.leaves()]

    for i in tree.leaves_to_root_iterator(include_leaves=False):
        tmp = []
        for c in tree.children(i):
            tmp.extend(result[c])
        result.append(tmp)

    return result


@hg.data_provider("gaussian_region_weights_model")
@hg.argument_helper(hg.CptHierarchy)
@hg.auto_cache
def attribute_gaussian_region_weights_model(tree, vertex_weights, leaf_graph=None):
    """
    Estimates a gaussian model (mean, (co-)variance) for leaf weights inside a node.

    The result is composed of two arrays:

        - the first one contains the mean value inside each node, scalar if vertex weights are scalar and vectorial otherwise,
        - the second one contains the variance of the values inside each node, scalar if vertex weights are scalar and a (biased) covariance matrix otherwise.

    Vertex weights must be scalar or 1 dimensional.

    **Provider name**: "gaussian_region_weights_model"

    :param tree: input tree (Concept :class:`~higra.CptHierarchy`)
    :param vertex_weights: vertex weights of the leaf graph of the input tree
    :param leaf_graph: leaf graph of the input tree (deduced from :class:`~higra.CptHierarchy`)
    :return: two arrays mean and variance
    """
    if leaf_graph is not None:
        vertex_weights = hg.linearize_vertex_weights(vertex_weights, leaf_graph)

    if vertex_weights.ndim > 2:
        raise ValueError("Vertex weight can either be scalar or 1 dimensional.")

    area = hg.attribute_area(tree, leaf_graph=leaf_graph)
    mean = hg.accumulate_sequential(tree, vertex_weights, hg.Accumulators.sum, leaf_graph)

    if vertex_weights.ndim == 1:
        # general case below would work but this is simpler
        mean /= area
        mean2 = hg.accumulate_sequential(tree, vertex_weights * vertex_weights, hg.Accumulators.sum, leaf_graph)
        mean2 /= area
        variance = mean2 - mean * mean
    else:
        mean /= area[:, None]
        tmp = vertex_weights[:, :, None] * vertex_weights[:, None, :]
        mean2 = hg.accumulate_sequential(tree, tmp, hg.Accumulators.sum, leaf_graph)
        mean2 /= area[:, None, None]

        variance = mean2 - mean[:, :, None] * mean[:, None, :]

    return mean, variance


@hg.data_provider("extrema")
@hg.auto_cache
def attribute_extrema(tree, altitudes):
    """
    Identify nodes in a hierarchy that represent extrema.

    An extremum of the hierarchy :math:`T` with altitudes :math:`alt` is a node :math:`n` of :math:`T` such that the
    altitude of any non leaf node included in :math:`n` is equal to the altitude of :math:`n` and the altitude of
    the parent of :math:`n` is different from the altitude of :math:`n`.

    The result is a boolean array such that :math:`result(n)` is ``True`` if the node :math:`n` is an extremum and ``False``
    otherwise.

    :param tree: Input tree
    :param altitudes: Tree node altitudes
    :return: a 1d boolean array
    """

    res = hg.cpp._attribute_extrema(tree, altitudes)

    return res


def __process_param_increasing_altitudes(tree, altitudes, increasing_altitudes):
    """
    Assuming that altitudes are monotone for the input tree, test if they are increasing or decreasing.

    :param tree:
    :param altitudes:
    :return:
    """
    if isinstance(increasing_altitudes, bool):
        return increasing_altitudes

    if increasing_altitudes == "auto":
        alt_root = altitudes[tree.root()]
        alt_min = np.min(altitudes[tree.num_leaves():])
        return bool(alt_root > alt_min)
    elif increasing_altitudes == "increasing":
        return True
    elif increasing_altitudes == "decreasing":
        return False
    else:
        raise ValueError("Unknown mode '" + str(increasing_altitudes) + "' valid values are 'auto', True, False, "
                                                                        "'increasing', and 'decreasing'.")


def attribute_extinction_value(tree, altitudes, attribute, increasing_altitudes="auto"):
    """
    The extinction value of a node :math:`n` of the input tree :math:`T` with increasing altitudes :math:`alt`
    for the increasing attribute :math:`att` is the equal to the threshold :math:`k` such that the node :math:`n`
    is still in an minima of :math:`t` when all nodes having an attribute value smaller than :math:`k` are removed.

    Formally, let :math:`\{M_i\}` be the set of minima of the hierarchy :math:`T` with altitudes :math:`alt`.
    Let :math:`prec` be a total ordering of :math:`\{M_i\}` such that :math:`M_i \prec M_j \Rightarrow alt(M_i) \leq alt(M_j)`.
    Let :math:`r(M_i)` be the smallest node of :math:`t` containing :math:`M_i` and another minima :math:`M_j` such
    that :math:`M_j \prec M_i`. The extinction value of :math:`M_i` is then defined as :math:`alt(r(M_i)) - alt(M_i)`.

    Extinction values of minima are then extended to other nodes in the tree with the following rules:

        - the extinction value of a non-leaf node :math:`n` which is not a minimum is defined as the largest
          extinction values among all the minima contained in :math:`n`
          (and 0 if :math:`n` does not contain any minima); and
        - the extinction value of a leaf node :math:`n` belonging to a minima :math:`M_i` is equal to the extinction
          value of :math:`M_i`. I :math:`n` does not belong to any minima its extinction value is 0.

    The function can also handle decreasing altitudes, in which case *minima* should be replaced by *maxima*
    in the description above. Possible values of :attr:`increasing_altitude` are:

        - ``'auto'``: the function will automatically determine if :attr:`altitudes` are increasing or decreasing (this has
          small computational cost but does not impact the runtime complexity).
        - ``True`` or ``'increasing'``: this means that altitudes are increasing from the leaves to the root
          (ie. for any node :math:`n`, :math:`altitudes(n) \leq altitudes(parent(n))`.
        - ``False`` or ``'decreasing'``: this means that altitudes are decreasing from the leaves to the root
          (ie. for any node :math:`n`, :math:`altitude(n) \geq altitude(parent(n))`.


    :param tree: Input tree
    :param altitudes: Tree node altitudes
    :param attribute: Tree node attribute
    :param increasing_altitudes: possible values 'auto', True, False, 'increasing', and 'decreasing'
    :return: a 1d array like :attr:`attribute`
    """
    inc = __process_param_increasing_altitudes(tree, altitudes, increasing_altitudes)

    altitudes, attribute = hg.cast_to_common_type(altitudes, attribute)

    res = hg.cpp._attribute_extinction_value(tree, altitudes, attribute, inc)

    return res


@hg.auto_cache
def attribute_height(tree, altitudes, increasing_altitudes="auto"):
    """
    In a tree :math:`T`, given that the altitudes of the nodes vary monotically from the leaves to the root,
    the height of a node :math:`n` of :math:`T` is equal to the difference between the altitude of the parent
    of :math:`n` and the altitude of the deepest non-leaf node in the subtree of :math:`T` rooted in :math:`n`.

    Possible values of :attr:`increasing_altitude` are:

        - ``'auto'``: the function will automatically determine if :attr:`altitudes` are increasing or decreasing (this has
          small computational cost but does not impact the runtime complexity).
        - ``True`` or ``'increasing'``: this means that altitudes are increasing from the leaves to the root
          (ie. for any node :math:`n`, :math:`altitudes(n) \leq altitudes(parent(n))`.
        - ``False`` or ``'decreasing'``: this means that altitudes are decreasing from the leaves to the root
          (ie. for any node :math:`n`, :math:`altitude(n) \geq altitude(parent(n))`.

    :param tree: Input tree
    :param altitudes: Tree node altitudes
    :param increasing_altitudes: possible values 'auto', True, False, 'increasing', and 'decreasing'
    :return: a 1d array like :attr:`altitudes`
    """
    inc = __process_param_increasing_altitudes(tree, altitudes, increasing_altitudes)

    res = hg.cpp._attribute_height(tree, altitudes, inc)

    return res


@hg.auto_cache
def attribute_dynamics(tree, altitudes, increasing_altitudes="auto"):
    """
    Given a node :math:`n` of the tree :math:`T`, the dynamics of :math:`n` is the difference between
    the altitude of the deepest minima of the subtree rooted in :math:`n` and the altitude
    of the closest ancestor of :math:`n` that has a deeper minima in its subtree. If no such
    ancestor exists then, the dynamics of :math:`n` is equal to the difference between the
    altitude of the highest node of the tree (the root) and the depth of the deepest minima.

    The dynamics is the *extinction values* (:func:`~higra.attribute_extinction_value`) for the attribute *height*
    (:func:`~higra.attribute_height`).

    Possible values of :attr:`increasing_altitude` are:

        - ``'auto'``: the function will automatically determine if :attr:`altitudes` are increasing or decreasing (this has
          small computational cost but does not impact the runtime complexity).
        - ``True`` or ``'increasing'``: this means that altitudes are increasing from the leaves to the root
          (ie. for any node :math:`n`, :math:`altitudes(n) \leq altitudes(parent(n))`.
        - ``False`` or ``'decreasing'``: this means that altitudes are decreasing from the leaves to the root
          (ie. for any node :math:`n`, :math:`altitude(n) \geq altitude(parent(n))`.


    :param tree: Input tree
    :param altitudes: Tree node altitudes
    :param increasing_altitudes: possible values 'auto', True, False, 'increasing', and 'decreasing'
    :return: a 1d array like :attr:`altitudes`
    """

    inc = __process_param_increasing_altitudes(tree, altitudes, increasing_altitudes)

    height = hg.attribute_height(tree, altitudes, inc)

    return hg.attribute_extinction_value(tree, altitudes, height, inc)
