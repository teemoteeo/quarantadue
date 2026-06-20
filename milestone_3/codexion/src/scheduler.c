/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   scheduler.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/19 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

static void	scheduler_enqueue_locked(t_simulation *sim, int coder_id)
{
	long long	priority;

	if (sim->scheduler_type == CODEX_FIFO)
		priority = sim->coders[coder_id - 1].wait_since;
	else
		priority = sim->coders[coder_id - 1].last_compile_start
			+ sim->time_to_burnout;
	heap_push(sim, coder_id, priority);
}

static int	scheduler_pop_front(t_simulation *sim, int *coder_id,
		long long *priority)
{
	if (!heap_pop(sim, coder_id, priority))
		return (0);
	return (1);
}

/*
 * Called with sched_mutex held and our turn confirmed.
 * Always returns with sched_mutex released.
 * Returns 1 if the dongle was claimed, 0 if it was busy (self re-enqueued).
 */
static int	scheduler_try_claim(t_simulation *sim, int coder_id, t_dongle *d)
{
	pthread_mutex_unlock(&sim->sched_mutex);
	if (dongle_try_acquire(d, coder_id))
		return (1);
	pthread_mutex_lock(&sim->sched_mutex);
	scheduler_enqueue_locked(sim, coder_id);
	pthread_mutex_unlock(&sim->sched_mutex);
	return (0);
}

/*
 * One scheduling attempt. Lock held on entry, released on exit.
 * Returns 1 = dongle claimed, -1 = stop requested, 0 = keep waiting.
 */
static int	scheduler_step(t_simulation *sim, int coder_id, t_dongle *d)
{
	int			front_id;
	long long	priority;

	if (check_stop(sim))
	{
		pthread_mutex_unlock(&sim->sched_mutex);
		return (-1);
	}
	if (!scheduler_pop_front(sim, &front_id, &priority))
	{
		scheduler_enqueue_locked(sim, coder_id);
		pthread_mutex_unlock(&sim->sched_mutex);
		return (0);
	}
	if (front_id != coder_id)
	{
		heap_push(sim, front_id, priority);
		pthread_mutex_unlock(&sim->sched_mutex);
		return (0);
	}
	return (scheduler_try_claim(sim, coder_id, d));
}

int	scheduler_request_single(t_simulation *sim, int coder_id, t_dongle *d)
{
	int	rc;

	pthread_mutex_lock(&sim->sched_mutex);
	scheduler_enqueue_locked(sim, coder_id);
	while (1)
	{
		rc = scheduler_step(sim, coder_id, d);
		if (rc == 1)
			return (0);
		if (rc == -1)
			return (-1);
		ft_usleep(1);
		pthread_mutex_lock(&sim->sched_mutex);
	}
}
