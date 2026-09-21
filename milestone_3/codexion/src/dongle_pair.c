/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   dongle_pair.c                                      :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/09/21 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/09/21 00:00:00 by teemoteeo       ###   ########.fr        */
/*                                                                            */
/* ************************************************************************** */

/* Acquisizione atomica della coppia di dongle: o si prendono tutti e due, o
 * non se ne prende nessuno. E' questo che rompe la condizione di Coffman
 * "hold and wait": un coder non tiene mai fermo un dongle mentre aspetta
 * l'altro, quindi non puo' affamare il vicino che di quel dongle ha bisogno. */

#include "codexion.h"

/*
 * Il mutex del dongle deve essere gia' tenuto dal chiamante. Il cooldown
 * scaduto viene consumato qui, cosi' la disponibilita' e' sempre valutata
 * sull'istante corrente.
 */
static int	dongle_is_available(t_dongle *d, long long now)
{
	if (d->state == DONGLE_COOLDOWN && now >= d->cooldown_until)
		d->state = DONGLE_FREE;
	return (d->state == DONGLE_FREE);
}

/*
 * I due mutex vengono presi sempre nell'ordine passato dal chiamante, che
 * e' l'ordine crescente di indice del dongle: due thread non possono quindi
 * incrociarsi e bloccarsi a vicenda qui dentro.
 * Con a == b (un solo coder, un solo dongle) si ricade sull'acquisizione
 * singola, altrimenti si bloccherebbe lo stesso mutex due volte.
 */
int	dongle_try_acquire_pair(t_dongle *a, t_dongle *b)
{
	long long	now;
	int			free_a;
	int			free_b;

	if (a == b)
		return (dongle_try_acquire(a));
	pthread_mutex_lock(&a->mutex);
	pthread_mutex_lock(&b->mutex);
	now = now_ms();
	free_a = dongle_is_available(a, now);
	free_b = dongle_is_available(b, now);
	if (free_a && free_b)
	{
		a->state = DONGLE_HELD;
		b->state = DONGLE_HELD;
	}
	pthread_mutex_unlock(&b->mutex);
	pthread_mutex_unlock(&a->mutex);
	return (free_a && free_b);
}
