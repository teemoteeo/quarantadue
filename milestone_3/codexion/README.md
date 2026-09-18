<i>Questo progetto è stato creato nell'ambito del curriculum 42 da teemoteeo.</i>

# Codexion

Una sfida di concorrenza e sincronizzazione: orchestrare più coder in competizione per dongle USB
limitati usando thread POSIX, mutex, variabili di condizione e uno scheduler con coda prioritaria
personalizzata (FIFO / EDF), prevenendo deadlock, starvation e burnout.

## Descrizione

Codexion simula coder seduti in un hub circolare, che condividono dongle USB per compilare codice quantistico.
Ogni coder ha bisogno di **due dongle** (sinistro e destro) per compilare. Dopo aver compilato, debuggano,
refactorizzano, poi riprovano a compilare — tutto prima della scadenza di burnout.

La sfida: **nessun coder deve andare in burnout**, nonostante:
- Dongle limitati (uno tra ogni coppia di coder)
- Periodo di cooldown del dongle dopo il rilascio
- Nessuna comunicazione tra i coder
- Due strategie di arbitraggio: FIFO (First In, First Out) e EDF (Earliest Deadline First)

### Problemi di Concorrenza Risolti

| Problema | Soluzione |
|---------|----------|
| **Mutua esclusione** | Ogni dongle protetto da `pthread_mutex_t` |
| **Deadlock** (Coffman: attesa circolare) | Acquisizione ordinata per indice; timeout con EDF |
| **Starvation** | EDF garantisce attesa limitata per parametri fattibili |
| **Race condition** | Tutto lo stato condiviso (dongle, log) protetto da mutex |
| **Rilevamento burnout preciso** | Thread monitor dedicato con `pthread_cond_timedwait` |
| **Interleaving dei log** | Output serializzato tramite mutex log globale |

### Architettura

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Coder 1  │  │ Coder 2  │  │ Coder 3  │  ...
│ (thread) │  │ (thread) │  │ (thread) │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │dongle0      │dongle1      │dongle2
  ┌──┴──────────┬──┴──────────┬──┴──────┐
  │   Dongle    │   Dongle    │ Dongle  │ ... (circolare)
  │  (mutex)    │  (mutex)    │ (mutex) │
  └─────────────┴─────────────┴─────────┘
                      │
              ┌───────┴────────┐
              │  Scheduler     │
              │  (FIFO / EDF)  │
              │  coda prior.   │
              └───────┬────────┘
                      │
              ┌───────┴────────┐
              │  Monitor       │
              │  (burnout)     │
              └────────────────┘
```

## Istruzioni

### Prerequisiti

- GCC o Clang con supporto C11
- Libreria POSIX threads (`-pthread`)
- `make`

### Compilazione

```bash
make
```

### Utilizzo

```bash
./codexion <numero_coder> <tempo_burnout_ms> <tempo_compilazione_ms> \
           <tempo_debug_ms> <tempo_refactor_ms> \
           <compilazioni_richieste> <cooldown_dongle_ms> \
           <scheduler>
```

**Argomenti:**
- `numero_coder` — Numero di coder (e dongle). Deve essere ≥ 1.
- `tempo_burnout_ms` — Millisecondi prima che un coder vada in burnout se non compila.
- `tempo_compilazione_ms` — Durata della compilazione (tiene 2 dongle).
- `tempo_debug_ms` — Durata della fase di debug.
- `tempo_refactor_ms` — Durata della fase di refactoring.
- `compilazioni_richieste` — La simulazione si ferma quando tutti i coder raggiungono questo numero.
- `cooldown_dongle_ms` — Il dongle è indisponibile per questo tempo dopo il rilascio.
- `scheduler` — `fifo` o `edf`.

**Esempio:**
```bash
./codexion 4 1500 200 200 200 3 100 fifo
```

### Formato Output

```
0 1 has taken a dongle
2 1 has taken a dongle
2 1 is compiling
202 1 is debugging
402 1 is refactoring
...
```

Ogni riga: `<timestamp_ms> <id_coder> <messaggio>`

### Pulizia

```bash
make fclean
```

### Regole Make

```bash
make        # Compila il binario codexion
make all    # Uguale a make
make clean  # Rimuove i file oggetto
make fclean # Rimuove binario e oggetti
make re     # Ricompila da zero
```

## Meccanismi di Sincronizzazione dei Thread

### Stato per Dongle (Mutex + Variabile di Condizione)

Ogni dongle è protetto da:
- `pthread_mutex_t` — protegge lo stato del dongle (libero, cooldown, in uso)
- `pthread_cond_t` — i coder aspettano qui quando il dongle non è disponibile

Quando un coder richiede un dongle:
1. Blocca il mutex del dongle
2. Se disponibile → lo prende, segnala i coder in attesa
3. Se in cooldown o occupato → `pthread_cond_wait`
4. Al risveglio → riprova ad acquisire (protezione contro wakeup spuri)

### Coda Prioritaria Personalizzata

Né FIFO né EDF possono usare una libreria standard. È implementato un min-heap binario:
- **Modalità FIFO**: chiave = timestamp di arrivo
- **Modalità EDF**: chiave = `last_compile_start + time_to_burnout` (deadline più vicina prima)

A parità di deadline (EDF), vince il coder con id minore.

### Thread Monitor

Un thread monitor dedicato gira in modo indipendente:
- Itera su tutti i coder ad alta frequenza
- Per ogni coder, controlla se `now - last_compile_start >= time_to_burnout`
- Se rileva burnout: lo registra entro 10ms, imposta il flag di stop globale, invia broadcast a tutte le variabili di condizione

### Serializzazione dei Log

Tutte le righe di output passano per un unico `pthread_mutex_t log_mutex`. La chiamata a `write` è protetta così nessun messaggio si sovrappone.

## Casi Limite Gestiti

### Prevenzione Deadlock

Scenario classico: Coder 1 tiene il dongle A, aspetta B; Coder 2 tiene B, aspetta A.

**Soluzione**: I coder acquisiscono sempre i dongle in ordine consistente (indice minore prima).
In modalità EDF, un timeout (`pthread_cond_timedwait`) previene l'attesa indefinita.

Condizioni di Coffman:
1. ✅ **Mutua esclusione** — Necessaria (i dongle sono esclusivi)
2. ✅ **Hold and wait** — I coder tengono un dongle mentre aspettano il secondo
3. ❌ **No preemption** — Rotta: EDF può interrompere tramite timeout
4. ❌ **Attesa circolare** — Rotta: acquisizione ordinata (indice minore prima)

### Prevenzione Starvation

- **FIFO**: Equo per definizione — il coder che aspetta da più tempo prende il dongle
- **EDF**: Serve prima la deadline più vicina; con parametri fattibili, nessun coder muore di fame.
La coda prioritaria garantisce inserimento ed estrazione O(log n).

### Gestione Cooldown

Dopo il rilascio, un dongle entra in cooldown per `cooldown_dongle_ms`. Durante il cooldown
risulta indisponibile. Il monitor traccia la scadenza del cooldown tramite `gettimeofday()`.

## Scelte di Design

### Perché Due Dongle per Coder?

Il requisito dei due dongle crea un problema classico di allocazione risorse: ogni coder ha bisogno
di due risorse adiacenti, forzando la coordinazione. Con N coder e N dongle in anello, al massimo
⌊N/2⌋ coder possono compilare contemporaneamente.

### Perché pthread_cond_timedwait per EDF?

Lo scheduling EDF richiede la possibilità di fare timeout su un coder in attesa se arriva uno con
priorità più alta. `pthread_cond_timedwait` permette un'attesa limitata, dopo la quale il coder
rivaluta la sua posizione.

### Perché una Coda Prioritaria Personalizzata?

Il soggetto richiede esplicitamente di implementare la coda prioritaria (heap) senza usare
equivalenti di libreria standard. Serve per capire la struttura dati sottostante.

### Perché un Thread Monitor?

Il rilevamento del burnout deve essere preciso (entro 10ms). Un thread separato che polling ad alta
frequenza è più semplice e affidabile rispetto a incorporare il rilevamento nel ciclo di ogni coder,
che potrebbe perdere una deadline se bloccato su un mutex.

## Risorse

- [POSIX Threads Programming](https://computing.llnl.gov/tutorials/pthreads/) — Tutorial pthreads LLNL
- [pthread_mutex_lock(3)](https://man7.org/linux/man-pages/man3/pthread_mutex_lock.3.html) — Man page mutex
- [pthread_cond_wait(3)](https://man7.org/linux/man-pages/man3/pthread_cond_wait.3.html) — Man page variabile di condizione
- [Deadlock e Condizioni di Coffman](https://en.wikipedia.org/wiki/Deadlock#Coffman_conditions) — Teoria della prevenzione deadlock
- [Earliest Deadline First Scheduling](https://en.wikipedia.org/wiki/Earliest_deadline_first_scheduling) — Teoria EDF
- [Priority Queue / Binary Heap](https://en.wikipedia.org/wiki/Binary_heap) — Struttura dati heap
- [gettimeofday(2)](https://man7.org/linux/man-pages/man2/gettimeofday.2.html) — Tempo ad alta risoluzione

### Utilizzo AI

L'AI è stata usata per:
- Progettare l'architettura di sincronizzazione dei thread
- Implementare la struttura dati coda prioritaria (heap)
- Debuggare race condition e scenari di deadlock
- Scrivere la logica di rilevamento burnout del thread monitor
- Strutturare il Makefile e il layout del progetto
- Documentare i pattern di concorrenza e i casi limite
