/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   push_swap.h                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/20 15:21:20 by timoteo           #+#    #+#             */
/*   Updated: 2026/01/28 15:37:28 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef PUSH_SWAP_H
# define PUSH_SWAP_H

# include <stdlib.h>
# include <unistd.h>
# include <stdio.h>
# include "libft/libft.h"

typedef struct s_node
{
	int				value;
	int				index;
	struct s_node	*next;
}	t_node;

typedef struct s_stack
{
	t_node	*top;
	int		size;
}	t_stack;

//utility functions

int		find_max(t_stack *stack);
int		find_min(t_stack *stack);
void	free_stack(t_stack *stack);
t_stack	*parse_input(int argc, char **argv, t_stack *a, t_stack *b);
t_stack	*init_stack(void);

//validation functions

int		is_valid_input(char *str);
int		has_duplicate(t_stack *stack, int value);
void	error_exit(t_stack *a, t_stack *b);

//index functions

void	assign_index(t_stack *stack);

//small sort functions

void	sort_two(t_stack *stack_a);
void	sort_three(t_stack *stack_a);
void	sort_four(t_stack *stack_a, t_stack *stack_b);
void	sort_five(t_stack *stack_a, t_stack *stack_b);

//cost functions

int		get_position(t_stack *stack, t_node *node);
int		find_target_pos(t_stack *stack_a, int b_index);
int		get_min_index_position(t_stack *stack);
int		calculate_cost(int pos_a, int pos_b, int size_a, int size_b);
t_node	*find_cheapest(t_stack *stack_a, t_stack *stack_b);
void	final_rotate(t_stack *a);

//turk sort

void	turk_sort(t_stack *a, t_stack *b);

//swap functions

void	swap(t_stack *stack);
void	sa(t_stack *stack_a);
void	sb(t_stack *stack_b);
void	ss(t_stack *stack_a, t_stack *stack_b);

//push functions

void	push(t_stack *from, t_stack *to);
void	pa(t_stack *stack_a, t_stack *stack_b);
void	pb(t_stack *stack_a, t_stack *stack_b);

//rotate functions

void	rotate(t_stack *stack);
void	ra(t_stack *stack_a);
void	rb(t_stack *stack_b);
void	rr(t_stack *stack_a, t_stack *stack_b);

//reverse rotate functions

void	reverse_rotate(t_stack *stack);
void	rra(t_stack *stack_a);
void	rrb(t_stack *stack_b);
void	rrr(t_stack *stack_a, t_stack *stack_b);

#endif
