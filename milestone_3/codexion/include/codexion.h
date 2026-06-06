/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   codexion.h                                         :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#             */
/*   Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef CODEXION_H
# define CODEXION_H

# include <pthread.h>
# include <sys/time.h>
# include <stdlib.h>
# include <unistd.h>

# define MAX_CODERS		256
# define BURNOUT_TOLERANCE_MS	10

typedef enum e_scheduler
{
	CODEX_FIFO,
	CODEX_EDF
}	t_scheduler;

typedef struct s_heap_node
{
	int			coder_id;
	long long	priority;	/* arrival time (FIFO) or deadline (EDF) */
}	t_heap_node;

typedef enum e_dongle_state
{
	DONGLE_FREE,
	DONGLE_HELD,
	DONGLE_COOLDOWN
}	t_dongle_state;

typedef struct s_simulation	t_simulation;

typedef struct s_dongle
{
	int				id;
	t_dongle_state	state;
	int				held_by;		/* coder_id, or -1 if free */
	long long		cooldown_until;	/* ms timestamp when cooldown ends */
	pthread_mutex_t	mutex;
	pthread_cond_t	cond;
	t_simulation	*sim;
}	t_dongle;

typedef enum e_coder_state
{
	CODER_IDLE,
	CODER_WAITING_DONGLE,
	CODER_COMPILING,
	CODER_DEBUGGING,
	CODER_REFACTORING,
	CODER_BURNED_OUT,
	CODER_DONE
}	t_coder_state;

typedef struct s_coder
{
	int				id;
	t_coder_state	state;
	int				compiles_done;
	long long		last_compile_start;	/* ms timestamp */
	long long		state_since;		/* ms timestamp of current state */
	pthread_t		thread;
	int				left_dongle;
	int				right_dongle;
	t_simulation	*sim;
}	t_coder;

typedef struct s_simulation
{
	int				nb_coders;
	int				time_to_burnout;
	int				time_to_compile;
	int				time_to_debug;
	int				time_to_refactor;
	int				compiles_required;
	int				dongle_cooldown_ms;
	t_scheduler		scheduler_type;

	t_coder			coders[MAX_CODERS];
	t_dongle		dongles[MAX_CODERS];

	pthread_mutex_t	stop_mutex;
	int				stop_flag;

	pthread_mutex_t	log_mutex;

	pthread_t		monitor_thread;
	long long		start_time;		/* simulation start timestamp (ms) */
	pthread_mutex_t	sched_mutex;
	t_heap_node		*wait_queue;
	int				wait_queue_size;
	int				wait_queue_capacity;
}	t_simulation;

/* main.c */
void		die(const char *msg);

/* parser.c */
int			parse_args(int argc, char **argv, t_simulation *sim);

/* logger.c */
long long	timestamp_ms(const t_simulation *sim);
void		log_msg(t_simulation *sim, int coder_id, const char *msg);

/* dongle.c */
void		dongle_init(t_dongle *d, int id, t_simulation *sim);
void		dongle_destroy(t_dongle *d);
int			dongle_try_acquire(t_dongle *d, int coder_id);
int			dongle_try_acquire_timed(t_dongle *d, int coder_id,
				long long deadline_ms);
void		dongle_release(t_dongle *d);
int			dongle_is_available(const t_dongle *d);
long long	now_ms(void);

/* coder.c */
void		*coder_routine(void *arg);
int			acquire_both_dongles(t_coder *c, t_dongle *left, t_dongle *right);
int			check_stop(t_simulation *sim);

/* heap.c */
void		heap_init(t_simulation *sim);
void		heap_destroy(t_simulation *sim);
void		heap_push(t_simulation *sim, int coder_id, long long priority);
int			heap_pop(t_simulation *sim, int *coder_id, long long *priority);
int			heap_is_empty(const t_simulation *sim);
void		heap_sift_up(t_heap_node *heap, int idx);
void		heap_sift_down(t_heap_node *heap, int size, int idx);

/* scheduler.c */
int			scheduler_request_single(t_simulation *sim, int coder_id,
				t_dongle *d);

/* monitor.c */
void		*monitor_routine(void *arg);

/* simulation.c */
void		simulation_init(t_simulation *sim);
void		simulation_run(t_simulation *sim);
void		simulation_cleanup(t_simulation *sim);
void		simulation_init_dongles(t_simulation *sim);
void		simulation_init_coders(t_simulation *sim);
void		simulation_init_last_compile(t_simulation *sim);
void		simulation_spawn_threads(t_simulation *sim);
void		simulation_join_threads(t_simulation *sim);

/* utils */
void		ft_usleep(long long ms);

#endif
