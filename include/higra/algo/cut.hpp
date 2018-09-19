/***************************************************************************
* Copyright ESIEE Paris (2018)                                             *
*                                                                          *
* Contributor(s) : Benjamin Perret                                         *
*                                                                          *
* Distributed under the terms of the CECILL-B License.                     *
*                                                                          *
* The full license is in the file LICENSE, distributed with this software. *
****************************************************************************/

#pragma once

#include "../graph.hpp"

namespace hg {

    /**
     * Labelize graph vertices according to the given graph cut.
     * Each edge having a non zero value in the given edge_weights
     * are assumed to be part of the cut.
     *
     * @tparam graph_t
     * @tparam T
     * @tparam label_type
     * @param graph
     * @param edge_weights
     * @return
     */
    template< typename graph_t,
            typename T>
    auto graph_cut_2_labelisation(const graph_t & graph,
                                  const xt::xexpression<T> & xedge_weights){
        HG_TRACE();
        auto & edge_weights = xedge_weights.derived_cast();
        hg_assert(edge_weights.dimension() == 1, "Edge weights must be scalar.");
        hg_assert(num_edges(graph) == edge_weights.size(),
                  "Edge weights size does not match graph number of edges.");
        stackv<index_t> stack;
        array_1d<index_t> labels = xt::empty<index_t>({num_vertices(graph)});
        labels.fill(invalid_index);

        index_t current_label = 0;
        for(auto v: vertex_iterator(graph)){
            if(labels(v) == invalid_index){
                current_label++;
                labels(v) = current_label;
                stack.push(v);
                while(!stack.empty()){
                    auto cv = stack.top();
                    stack.pop();
                    for(auto edge_index: out_edge_index_iterator(cv, graph)){
                        if(edge_weights(edge_index) == 0){
                            auto e = edge(edge_index, graph);
                            auto n = other_vertex(e, cv, graph);
                            if(labels(n) == invalid_index){
                                labels(n) = current_label;
                                stack.push(n);
                            }
                        }
                    }
                }
            }
        }

        return labels;
    };




}