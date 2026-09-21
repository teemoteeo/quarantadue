/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   dongle.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/21 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

/* Macchina a stati di un singolo dongle: init/destroy, try-acquire e release
 * (che lo manda in cooldown e sveglia i coder in attesa). */

#include "codexion.h"

void	dongle_init(t_dongle *d, t_simulation *sim)
{
	d->state = DONGLE_FREE;
	d->cooldown_until = 0;
	d->sim = sim;
	pthread_mutex_init(&d->mutex, NULL);
	pthread_mutex_init(&d->sched.mutex, NULL);
	pthread_cond_init(&d->sched.cond, NULL);
	d->sched.size = 0;
}

void	dongle_destroy(t_dongle *d)
{
	pthread_mutex_destroy(&d->mutex);
	pthread_mutex_destroy(&d->sched.mutex);
	pthread_cond_destroy(&d->sched.cond);
}

long long	now_ms(void)
{
	struct timeval	tv;

	gettimeofday(&tv, NULL);
	return ((long long)tv.tv_sec * 1000 + tv.tv_usec / 1000);
}

void	dongle_release(t_dongle *d)
{
	pthread_mutex_lock(&d->mutex);
	d->state = DONGLE_COOLDOWN;
	d->cooldown_until = now_ms() + d->sim->dongle_cooldown_ms;
	pthread_mutex_unlock(&d->mutex);
	pthread_mutex_lock(&d->sched.mutex);
	pthread_cond_broadcast(&d->sched.cond);
	pthread_mutex_unlock(&d->sched.mutex);
}
