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

/* Livello di fairness: ogni dongle ha la sua coda di priorità (FIFO o EDF).
 * Un coder si mette in fila su ENTRAMBI i dongle che gli servono, così
 * nessun vicino può portargliene via uno mentre lui aspetta l'altro. */

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

/* Mette il coder in fila su questo dongle con la priorità della politica. */
void	scheduler_enqueue(t_simulation *sim, t_sched *sq, int coder_id)
{
	pthread_mutex_lock(&sq->mutex);
	scheduler_enqueue_locked(sim, sq, coder_id);
	pthread_mutex_unlock(&sq->mutex);
}

/* Toglie il coder dalla fila e risveglia chi era dietro di lui. */
void	scheduler_dequeue(t_sched *sq, int coder_id)
{
	pthread_mutex_lock(&sq->mutex);
	heap_remove_by_id(sq, coder_id);
	pthread_cond_broadcast(&sq->cond);
	pthread_mutex_unlock(&sq->mutex);
}

/*
 * Permesso di prendere questo dongle: o non c'è nessuno in fila, o tocca
 * proprio a noi. È questa la veto che impedisce a un vicino di portarci via
 * un dongle mentre lo stiamo aspettando, anche se il vicino non si è messo
 * in fila qui perché per lui è il dongle di indice alto.
 */
int	scheduler_may_take(t_sched *sq, int coder_id)
{
	int	allowed;

	pthread_mutex_lock(&sq->mutex);
	allowed = (sq->size == 0 || sq->queue[0].coder_id == coder_id);
	pthread_mutex_unlock(&sq->mutex);
	return (allowed);
}

/*
 * Attesa limitata a 1 ms sulla cond del dongle. Il limite serve perché la
 * fine di un cooldown è un evento di tempo e non manda nessun broadcast:
 * senza timeout un coder in attesa non si accorgerebbe mai della scadenza.
 * Un release o uno stop, invece, svegliano subito con un broadcast.
 */
void	scheduler_wait_short(t_sched *sq)
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
	pthread_mutex_lock(&sq->mutex);
	pthread_cond_timedwait(&sq->cond, &sq->mutex, &ts);
	pthread_mutex_unlock(&sq->mutex);
}
