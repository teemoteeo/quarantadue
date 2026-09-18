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
 * Attesa limitata sulla sched_cond del dongle (1 ms). Necessaria mentre il
 * dongle è in cooldown: la scadenza è basata sul tempo e non manda broadcast.
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
 * Siamo la radice dello heap per questo dongle: proviamo ad acquisirlo.
 * sq->mutex è tenuto in entrata e in uscita. Restituisce 1 se acquisito,
 * 0 se occupato (attende brevemente).
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
 * Blocca finché questo coder è la radice della coda del dongle e lo possiede.
 * I coder non-radice dormono sulla sched_cond del dongle. Restituisce 0 in
 * caso di successo, -1 se è stata richiesta la fermata.
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
