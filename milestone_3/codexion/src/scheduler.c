/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   scheduler.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/*
 * Must be called with sched_mutex held.
 */
static void	scheduler_enqueue_locked(t_simulation *sim, int coder_id)
{
	long long	priority;

	if (sim->scheduler_type == CODEX_FIFO)
		priority = now_ms();
	else
		priority = sim->coders[coder_id - 1].last_compile_start
			+ sim->time_to_burnout;
	heap_push(sim, coder_id, priority);
}

static int	scheduler_get_front(t_simulation *sim, int coder_id, int *front_id)
{
	pthread_mutex_lock(&sim->sched_mutex);
	if (heap_is_empty(sim))
	{
		pthread_mutex_unlock(&sim->sched_mutex);
		return (0);
	}
	*front_id = sim->wait_queue[0].coder_id;
	pthread_mutex_unlock(&sim->sched_mutex);
	return (*front_id == coder_id);
}

static int	scheduler_try_claim(t_simulation *sim, int coder_id, t_dongle *d)
{
	int			acquired;
	int			front_id;
	long long	front_prio;

	acquired = dongle_try_acquire(d, coder_id);
	if (!acquired)
	{
		pthread_mutex_lock(&sim->sched_mutex);
		heap_pop(sim, &front_id, &front_prio);
		scheduler_enqueue_locked(sim, coder_id);
		pthread_mutex_unlock(&sim->sched_mutex);
		return (0);
	}
	pthread_mutex_lock(&sim->sched_mutex);
	heap_pop(sim, &front_id, &front_prio);
	pthread_mutex_unlock(&sim->sched_mutex);
	return (1);
}

int	scheduler_request_single(t_simulation *sim, int coder_id, t_dongle *d)
{
	int	front_id;

	pthread_mutex_lock(&sim->sched_mutex);
	scheduler_enqueue_locked(sim, coder_id);
	pthread_mutex_unlock(&sim->sched_mutex);
	while (1)
	{
		if (check_stop(sim))
			return (-1);
		if (!scheduler_get_front(sim, coder_id, &front_id))
		{
			ft_usleep(1);
			continue ;
		}
		if (scheduler_try_claim(sim, coder_id, d))
			return (0);
		ft_usleep(1);
	}
}
