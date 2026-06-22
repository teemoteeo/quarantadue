/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   scheduler.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/21 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"
#include <time.h>

static void	scheduler_enqueue_locked(t_simulation *sim, t_sched *sq,
				int coder_id)
{
	long long	priority;

	if (sim->scheduler_type == CODEX_FIFO)
		priority = sim->coders[coder_id - 1].wait_since;
	else
		priority = sim->coders[coder_id - 1].last_compile_start
			+ sim->time_to_burnout;
	heap_push(sq, coder_id, priority);
}

/*
 * Bounded wait on the per-dongle sched_cond (1 ms). Needed while the dongle
 * is in cooldown: cooldown expiry is time-based and fires no broadcast.
 */
static void	scheduler_wait_short(t_sched *sq)
{
	struct timespec	ts;
	struct timeval	tv;

	gettimeofday(&tv, NULL);
	ts.tv_sec = tv.tv_sec;
	ts.tv_nsec = tv.tv_usec * 1000 + 1000000;
	if (ts.tv_nsec >= 1000000000)
	{
		ts.tv_sec += 1;
		ts.tv_nsec -= 1000000000;
	}
	pthread_cond_timedwait(&sq->cond, &sq->mutex, &ts);
}

/*
 * We are the heap root for this dongle: attempt to claim it. sq->mutex is
 * held on entry and exit. Returns 1 if claimed, 0 if busy (waits briefly).
 */
static int	scheduler_try_as_root(t_sched *sq, int coder_id, t_dongle *d)
{
	int	got;

	pthread_mutex_unlock(&sq->mutex);
	got = dongle_try_acquire(d);
	pthread_mutex_lock(&sq->mutex);
	if (got)
	{
		heap_remove_by_id(sq, coder_id);
		pthread_cond_broadcast(&sq->cond);
		return (1);
	}
	scheduler_wait_short(sq);
	return (0);
}

/*
 * Block until this coder is the root of this dongle's queue and owns it.
 * Non-root coders sleep on the dongle's sched_cond. Returns 0 on success,
 * -1 if stop was requested.
 */
int	scheduler_request_single(t_simulation *sim, int coder_id, t_dongle *d)
{
	t_sched	*sq;

	sq = &d->sched;
	pthread_mutex_lock(&sq->mutex);
	scheduler_enqueue_locked(sim, sq, coder_id);
	while (1)
	{
		if (check_stop(sim))
		{
			heap_remove_by_id(sq, coder_id);
			pthread_mutex_unlock(&sq->mutex);
			return (-1);
		}
		if (sq->queue[0].coder_id != coder_id)
			pthread_cond_wait(&sq->cond, &sq->mutex);
		else if (scheduler_try_as_root(sq, coder_id, d))
		{
			pthread_mutex_unlock(&sq->mutex);
			return (0);
		}
	}
}
