/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   heap.c                                             :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/22 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/*
 * Il soggetto fissa un anello coder/dongle: ogni dongle è conteso esattamente
 * dai suoi 2 vicini, quindi la coda ha al massimo 2 elementi. Il minimo sta
 * all'indice 0, mantenuto con un singolo confronto al push.
 */
static int	node_is_smaller(t_heap_node a, t_heap_node b)
{
	if (a.priority != b.priority)
		return (a.priority < b.priority);
	return (a.coder_id < b.coder_id);
}

void	heap_init(t_sched *sq)
{
	sq->size = 0;
}

void	heap_push(t_sched *sq, int coder_id, long long priority)
{
	t_heap_node	node;

	node.coder_id = coder_id;
	node.priority = priority;
	if (sq->size == 0 || node_is_smaller(sq->queue[0], node))
		sq->queue[sq->size] = node;
	else
	{
		sq->queue[1] = sq->queue[0];
		sq->queue[0] = node;
	}
	sq->size++;
}

void	heap_remove_by_id(t_sched *sq, int coder_id)
{
	int	i;

	i = 0;
	while (i < sq->size)
	{
		if (sq->queue[i].coder_id == coder_id)
		{
			sq->size--;
			if (i < sq->size)
				sq->queue[i] = sq->queue[sq->size];
			return ;
		}
		i++;
	}
}
