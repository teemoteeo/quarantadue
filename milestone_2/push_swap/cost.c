/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   cost.c                                             :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/01/28 16:00:00 by tcostant          #+#    #+#             */
/*   Updated: 2026/01/28 19:09:14 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

int	get_position(t_stack *stack, t_node *node)
{
	t_node	*current;
	int		pos;

	current = stack->top;
	pos = 0;
	while (current)
	{
		if (current == node)
			return (pos);
		pos++;
		current = current->next;
	}
	return (-1);
}

int	find_target_pos(t_stack *stack_a, int b_index)
{
	t_node	*current;
	int		target_idx;
	int		target_pos;
	int		pos;

	current = stack_a->top;
	target_idx = 2147483647;
	target_pos = 0;
	pos = 0;
	while (current)
	{
		if (current->index > b_index && current->index < target_idx)
		{
			target_idx = current->index;
			target_pos = pos;
		}
		pos++;
		current = current->next;
	}
	if (target_idx == 2147483647)
		target_pos = get_min_index_position(stack_a);
	return (target_pos);
}

int	get_min_index_position(t_stack *stack)
{
	t_node	*current;
	int		min_idx;
	int		min_pos;
	int		pos;

	current = stack->top;
	min_idx = current->index;
	min_pos = 0;
	pos = 0;
	while (current)
	{
		if (current->index < min_idx)
		{
			min_idx = current->index;
			min_pos = pos;
		}
		pos++;
		current = current->next;
	}
	return (min_pos);
}

int	calculate_cost(int pos_a, int pos_b, int size_a, int size_b)
{
	int	cost_a;
	int	cost_b;
	int	cost;

	if (pos_a <= size_a / 2)
		cost_a = pos_a;
	else
		cost_a = size_a - pos_a;
	if (pos_b <= size_b / 2)
		cost_b = pos_b;
	else
		cost_b = size_b - pos_b;
	if ((pos_a <= size_a / 2 && pos_b <= size_b / 2)
		|| (pos_a > size_a / 2 && pos_b > size_b / 2))
	{
		if (cost_a > cost_b)
			cost = cost_a;
		else
			cost = cost_b;
	}
	else
		cost = cost_a + cost_b;
	return (cost);
}

t_node	*find_cheapest(t_stack *stack_a, t_stack *stack_b)
{
	t_node	*current;
	t_node	*cheapest;
	int		min_cost;
	int		cost;
	int		pos_b;

	current = stack_b->top;
	cheapest = current;
	min_cost = 2147483647;
	pos_b = 0;
	while (current)
	{
		cost = calculate_cost(find_target_pos(stack_a, current->index),
				pos_b, stack_a->size, stack_b->size);
		if (cost < min_cost)
		{
			min_cost = cost;
			cheapest = current;
		}
		pos_b++;
		current = current->next;
	}
	return (cheapest);
}
