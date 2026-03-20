/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   turk_sort.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/01/28 16:00:00 by tcostant          #+#    #+#             */
/*   Updated: 2026/01/29 16:48:51 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

static void	rotate_stacks(t_stack *a, t_stack *b, int *pos, int *rev)
{
	while (pos[0] > 0 && pos[1] > 0 && !rev[0] && !rev[1])
	{
		rr(a, b);
		pos[0]--;
		pos[1]--;
	}
	while (pos[0] > 0 && pos[1] > 0 && rev[0] && rev[1])
	{
		rrr(a, b);
		pos[0]--;
		pos[1]--;
	}
}

static void	finish_rotations(t_stack *a, t_stack *b, int *pos, int *rev)
{
	while (pos[0]-- > 0)
	{
		if (rev[0])
			rra(a);
		else
			ra(a);
	}
	while (pos[1]-- > 0)
	{
		if (rev[1])
			rrb(b);
		else
			rb(b);
	}
}

static void	move_to_top(t_stack *a, t_stack *b, int pos_a, int pos_b)
{
	int	pos[2];
	int	rev[2];

	rev[0] = (pos_a > a->size / 2);
	rev[1] = (pos_b > b->size / 2);
	if (rev[0])
		pos[0] = a->size - pos_a;
	else
		pos[0] = pos_a;
	if (rev[1])
		pos[1] = b->size - pos_b;
	else
		pos[1] = pos_b;
	rotate_stacks(a, b, pos, rev);
	finish_rotations(a, b, pos, rev);
}

static void	push_back_to_a(t_stack *a, t_stack *b)
{
	t_node	*cheapest;

	while (b->size > 0)
	{
		cheapest = find_cheapest(a, b);
		move_to_top(a, b, find_target_pos(a, cheapest->index),
			get_position(b, cheapest));
		pa(a, b);
	}
}

void	turk_sort(t_stack *a, t_stack *b)
{
	assign_index(a);
	if (a->size == 2)
		sort_two(a);
	else if (a->size == 3)
		sort_three(a);
	else if (a->size == 4)
		sort_four(a, b);
	else if (a->size == 5)
		sort_five(a, b);
	else
	{
		while (a->size > 3)
			pb(a, b);
		sort_three(a);
		push_back_to_a(a, b);
		final_rotate(a);
	}
}
