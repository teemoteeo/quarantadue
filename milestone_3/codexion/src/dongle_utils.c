/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   dongle_utils.c                                     :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

static int	dongle_try_acquire_timed_loop(t_dongle *d,
		long long deadline_ms)
{
	long long		dl;
	struct timespec	ts;

	while (1)
	{
		if (d->state == DONGLE_COOLDOWN && now_ms() >= d->cooldown_until)
			d->state = DONGLE_FREE;
		if (d->state == DONGLE_FREE)
			return (1);
		dl = now_ms();
		if (dl >= deadline_ms)
			return (0);
		ts.tv_sec = (deadline_ms / 1000);
		ts.tv_nsec = ((deadline_ms % 1000) * 1000000);
		pthread_cond_timedwait(&d->cond, &d->mutex, &ts);
	}
}

int	dongle_try_acquire_timed(t_dongle *d, int coder_id,
		long long deadline_ms)
{
	int	ret;

	pthread_mutex_lock(&d->mutex);
	ret = dongle_try_acquire_timed_loop(d, deadline_ms);
	if (ret)
	{
		d->state = DONGLE_HELD;
		d->held_by = coder_id;
	}
	pthread_mutex_unlock(&d->mutex);
	return (ret);
}

int	dongle_is_available(const t_dongle *d)
{
	if (d->state == DONGLE_FREE)
		return (1);
	if (d->state == DONGLE_COOLDOWN && now_ms() >= d->cooldown_until)
		return (1);
	return (0);
}
