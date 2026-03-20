/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   push_swap.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: timoteo <marvin@42.fr>                     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/20 15:19:35 by timoteo           #+#    #+#             */
/*   Updated: 2026/01/29 19:17:49 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"
#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>

t_stack	*init_stack(void)
{
	t_stack	*stack;

	stack = malloc(sizeof(t_stack));
	if (!stack)
		return (NULL);
	stack->top = NULL;
	stack->size = 0;
	return (stack);
}

void	free_stack(t_stack *stack)
{
	t_node	*current;
	t_node	*next;

	current = stack->top;
	while (current)
	{
		next = current->next;
		free(current);
		current = next;
	}
	free(stack);
}

t_stack	*parse_input(int argc, char **argv, t_stack *a, t_stack *b)
{
	int		i;
	long	num;
	t_node	*new_node;

	i = argc - 1;
	while (i >= 1)
	{
		if (!is_valid_input(argv[i]))
			error_exit(a, b);
		num = ft_atol(argv[i]);
		if (num > 2147483647 || num < -2147483648)
			error_exit(a, b);
		if (has_duplicate(a, (int)num))
			error_exit(a, b);
		new_node = malloc(sizeof(t_node));
		if (!new_node)
			error_exit(a, b);
		new_node->value = (int)num;
		new_node->next = a->top;
		a->top = new_node;
		a->size++;
		i--;
	}
	return (a);
}

int	is_sorted(t_stack *stack)
{
	t_node	*current;

	if (stack->size < 2)
		return (1);
	current = stack->top;
	while (current && current->next)
	{
		if (current->value > current->next->value)
			return (0);
		current = current->next;
	}
	return (1);
}

int	main(int argc, char **argv)
{
	t_stack	*a;
	t_stack	*b;

	if (argc < 2)
		return (0);
	a = init_stack();
	b = init_stack();
	parse_input(argc, argv, a, b);
	if (is_sorted(a))
	{
		free_stack(a);
		free_stack(b);
		return (0);
	}
	turk_sort(a, b);
	free_stack(a);
	free_stack(b);
	return (0);
}
