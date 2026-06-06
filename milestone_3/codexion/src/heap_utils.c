/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   heap_utils.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

static void	heap_swap(t_heap_node *a, t_heap_node *b)
{
	t_heap_node	tmp;

	tmp = *a;
	*a = *b;
	*b = tmp;
}

static int	is_smaller(const t_heap_node *a, const t_heap_node *b)
{
	if (a->priority != b->priority)
		return (a->priority < b->priority);
	return (a->coder_id < b->coder_id);
}

void	heap_sift_up(t_heap_node *heap, int idx)
{
	int	parent;

	while (idx > 0)
	{
		parent = (idx - 1) / 2;
		if (is_smaller(&heap[idx], &heap[parent]))
		{
			heap_swap(&heap[idx], &heap[parent]);
			idx = parent;
		}
		else
			break ;
	}
}

void	heap_sift_down(t_heap_node *heap, int size, int idx)
{
	int	left;
	int	right;
	int	smallest;

	while (1)
	{
		left = 2 * idx + 1;
		right = 2 * idx + 2;
		smallest = idx;
		if (left < size && is_smaller(&heap[left], &heap[smallest]))
			smallest = left;
		if (right < size && is_smaller(&heap[right], &heap[smallest]))
			smallest = right;
		if (smallest == idx)
			break ;
		heap_swap(&heap[idx], &heap[smallest]);
		idx = smallest;
	}
}
