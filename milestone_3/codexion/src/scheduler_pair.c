/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   scheduler_pair.c                                   :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/09/21 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/09/21 00:00:00 by teemoteeo       ###   ########.fr        */
/*                                                                            */
/* ************************************************************************** */

/* Richiesta arbitrata della coppia di dongle. Il coder si mette in fila sul
 * dongle di indice più basso, ma per prendere la coppia deve avere il via
 * libera su ENTRAMBI: un dongle su cui un altro coder è in testa alla fila
 * non è prendibile. Senza quel veto due vicini possono alternarsi sui due
 * dongle di chi sta in mezzo e affamarlo. */

#include "codexion.h"

/*
 * Via libera su tutti e due i dongle? Allora tentiamo la presa atomica.
 * Con d1 == d2 (un solo coder) c'è una sola fila da controllare.
 */
static int	pair_is_ready(int coder_id, t_dongle *d1, t_dongle *d2)
{
	if (!scheduler_may_take(&d1->sched, coder_id))
		return (0);
	if (d1 != d2 && !scheduler_may_take(&d2->sched, coder_id))
		return (0);
	return (dongle_try_acquire_pair(d1, d2));
}

/*
 * Un coder che ha passato metà del suo tempo di burnout senza compilare si
 * mette in fila anche sul dongle alto. Così il veto copre entrambi i suoi
 * dongle e i vicini non possono più alternarsi sottraendoglieli.
 * L'escalation vale solo per chi sta davvero rischiando: se scattasse per
 * tutti, ogni coder bloccherebbe entrambi i vicini e la simulazione si
 * serializzerebbe, perdendo le compilazioni in parallelo.
 */
static int	should_escalate(t_simulation *sim, int coder_id)
{
	t_coder_state	st;
	long long		last;

	read_coder_state(sim, coder_id - 1, &st, &last);
	return (now_ms() - last >= sim->time_to_burnout / 2);
}

static void	pair_leave_queues(int coder_id, t_dongle *d1, t_dongle *d2,
				int escalated)
{
	scheduler_dequeue(&d1->sched, coder_id);
	if (escalated)
		scheduler_dequeue(&d2->sched, coder_id);
}

/*
 * Restituisce 0 con entrambi i dongle in mano, -1 se è stata richiesta la
 * fermata. Finché il tentativo fallisce non si tiene niente: nessun
 * hold-and-wait, quindi nessun deadlock possibile.
 */
int	scheduler_request_pair(t_simulation *sim, int coder_id, t_dongle *d1,
		t_dongle *d2)
{
	int	up;

	up = 0;
	scheduler_enqueue(sim, &d1->sched, coder_id);
	while (1)
	{
		if (check_stop(sim))
		{
			pair_leave_queues(coder_id, d1, d2, up);
			return (-1);
		}
		if (pair_is_ready(coder_id, d1, d2))
		{
			pair_leave_queues(coder_id, d1, d2, up);
			return (0);
		}
		if (!up && d1 != d2 && should_escalate(sim, coder_id))
		{
			scheduler_enqueue(sim, &d2->sched, coder_id);
			up = 1;
		}
		scheduler_wait_short(&d1->sched);
	}
}
