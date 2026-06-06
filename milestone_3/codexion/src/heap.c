/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   heap.c                                             :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"
#include <stdlib.h>
#include <string.h>

/* Min-heap: key = priority (arrival time/EDF deadline), tie by coder_id. */

#define HEAP_INIT_CAP	16

void	heap_init(t_simulation *sim)
{
	sim->wait_queue_capacity = HEAP_INIT_CAP;
	sim->wait_queue = malloc(sizeof(t_heap_node) * sim->wait_queue_capacity);
	if (!sim->wait_queue)
		die("malloc failed");
	sim->wait_queue_size = 0;
}

void	heap_destroy(t_simulation *sim)
{
	free(sim->wait_queue);
	sim->wait_queue = NULL;
	sim->wait_queue_size = 0;
	sim->wait_queue_capacity = 0;
}

void	heap_push(t_simulation *sim, int coder_id, long long priority)
{
	if (sim->wait_queue_size >= sim->wait_queue_capacity)
	{
		sim->wait_queue_capacity *= 2;
		sim->wait_queue = realloc(sim->wait_queue,
				sizeof(t_heap_node) * sim->wait_queue_capacity);
		if (!sim->wait_queue)
			die("realloc failed");
	}
	sim->wait_queue[sim->wait_queue_size].coder_id = coder_id;
	sim->wait_queue[sim->wait_queue_size].priority = priority;
	heap_sift_up(sim->wait_queue, sim->wait_queue_size);
	sim->wait_queue_size++;
}

int	heap_pop(t_simulation *sim, int *coder_id, long long *priority)
{
	if (sim->wait_queue_size == 0)
		return (0);
	*coder_id = sim->wait_queue[0].coder_id;
	*priority = sim->wait_queue[0].priority;
	sim->wait_queue_size--;
	if (sim->wait_queue_size > 0)
	{
		sim->wait_queue[0] = sim->wait_queue[sim->wait_queue_size];
		heap_sift_down(sim->wait_queue, sim->wait_queue_size, 0);
	}
	return (1);
}

int	heap_is_empty(const t_simulation *sim)
{
	return (sim->wait_queue_size == 0);
}
