/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   dongle.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"
#include <sys/time.h>

void	dongle_init(t_dongle *d, int id, t_simulation *sim)
{
	d->id = id;
	d->state = DONGLE_FREE;
	d->held_by = -1;
	d->cooldown_until = 0;
	d->sim = sim;
	pthread_mutex_init(&d->mutex, NULL);
	pthread_cond_init(&d->cond, NULL);
}

void	dongle_destroy(t_dongle *d)
{
	pthread_mutex_destroy(&d->mutex);
	pthread_cond_destroy(&d->cond);
}

long long	now_ms(void)
{
	struct timeval	tv;

	gettimeofday(&tv, NULL);
	return ((long long)tv.tv_sec * 1000 + tv.tv_usec / 1000);
}

int	dongle_try_acquire(t_dongle *d, int coder_id)
{
	int	ret;

	pthread_mutex_lock(&d->mutex);
	ret = 0;
	if (d->state == DONGLE_COOLDOWN && now_ms() >= d->cooldown_until)
		d->state = DONGLE_FREE;
	if (d->state == DONGLE_FREE)
	{
		d->state = DONGLE_HELD;
		d->held_by = coder_id;
		ret = 1;
	}
	pthread_mutex_unlock(&d->mutex);
	return (ret);
}

void	dongle_release(t_dongle *d)
{
	pthread_mutex_lock(&d->mutex);
	d->state = DONGLE_COOLDOWN;
	d->cooldown_until = now_ms() + d->sim->dongle_cooldown_ms;
	d->held_by = -1;
	pthread_cond_broadcast(&d->cond);
	pthread_mutex_unlock(&d->mutex);
}
