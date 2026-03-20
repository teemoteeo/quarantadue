/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   index.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/01/28 16:00:00 by tcostant          #+#    #+#             */
/*   Updated: 2026/01/29 15:40:28 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

static t_node	*get_min_unindexed(t_stack *stack)
{
	t_node	*current;
	t_node	*min_node;
	int		min;

	current = stack->top;
	min_node = NULL;
	min = 2147483647;
	while (current)
	{
		if (current->index == -1 && current->value < min)
		{
			min = current->value;
			min_node = current;
		}
		current = current->next;
	}
	return (min_node);
}

void	assign_index(t_stack *stack)
{
	t_node	*current;
	t_node	*min_node;
	int		index;

	current = stack->top;
	while (current)
	{
		current->index = -1;
		current = current->next;
	}
	index = 0;
	while (index < stack->size)
	{
		min_node = get_min_unindexed(stack);
		if (min_node)
			min_node->index = index;
		index++;
	}
}
