<i>Questo progetto è stato creato come parte del curriculum 42 da tcostant.</i>

# Call Me Maybe

Ehi, ci siamo appena conosciuti, ed è una pazzia, ma ecco il mio numero quindi...

Un sistema di function calling che usa il decoding vincolato con Qwen3-0.6B, un piccolo modello
linguistico da 0.6B parametri. Il sistema traduce prompt in linguaggio naturale in chiamate di
funzione strutturate ed eseguibili, con argomenti tipizzati.

## Descrizione

Call Me Maybe implementa una pipeline di decoding vincolato che garantisce il 100% di output JSON
validi per il function calling, anche con modelli linguistici piccoli che altrimenti fallirebbero
oltre il 70% delle volte. Il progetto mostra come una guida strutturale possa ottenere
un'affidabilità quasi perfetta da modelli compatti.

### Come Funziona

1. **Catalogo di Funzioni**: Le funzioni disponibili sono definite con nomi, tipi di parametri e
   descrizioni
2. **Costruzione del Contesto**: Si costruisce un prompt che combina il catalogo di funzioni con
   la richiesta dell'utente
3. **Decoding Vincolato**: Ad ogni step di generazione dei token, i token non validi (quelli che
   romperebbero la struttura JSON o lo schema) vengono mascherati a `-inf`
4. **Selezione del Token**: Solo i token validi vengono considerati, così l'output rispetta lo
   schema atteso

### Caratteristiche Principali

- Decoding vincolato tramite mascheramento dei token a livello di vocabolario
- Supporto per i tipi JSON number, string e boolean
- Validazione della grammatica basata su DFA per i valori JSON
- Rilevamento di loop per pattern stile regex
- Fallback morbido per i casi limite

## Istruzioni

### Installazione

```bash
uv sync
```

### Utilizzo

Lancia la pipeline di function calling:

```bash
make run
# oppure
uv run python -m src \
    --functions_definition data/input/functions_definition.json \
    --input data/input/function_calling_tests.json \
    --output data/output/function_calling_results.json
```

### Modalità Debug

Esegui con l'output di debug che mostra le decisioni intermedie del decoding:

```bash
make debug
```

### Linting

Controlla la qualità del codice:

```bash
make lint
```

### Pulizia

Rimuovi i file generati:

```bash
make clean
```

## Spiegazione dell'Algoritmo

### Approccio del Decoding Vincolato

Il decoder lavora a livello di token con un approccio basato su maschere:

1. **Mascheramento a Livello di Token**: Per ogni step di generazione, il modello produce i logit
   per tutti i possibili token successivi
2. **Validazione della Grammatica**: I token vengono validati contro un DFA che rappresenta la
   grammatica attesa
3. **Mascheramento dei Token Non Validi**: I token che romperebbero la struttura JSON o
   violerebbero lo schema vengono mascherati a `-inf`
4. **Selezione Greedy**: Si sceglie il token valido con punteggio più alto

### Tre Modalità di Grammatica

Il decoder usa una logica di validazione separata per:

- **Selezione del Nome di Funzione**: Vincolata a combaciare con uno dei nomi di funzione
  disponibili
- **JSON Number**: Valida interi con segno e decimali con parte frazionaria opzionale
- **JSON String**: Gestisce le sequenze di escape e garantisce UTF-8 valido dopo il decoding

### Mappatura da Token a Testo

Un componente cruciale è la mappatura `id_to_text` che traduce gli ID del vocabolario nella loro
rappresentazione testuale letterale. Questa mappatura viene costruita così:

1. Si carica il JSON del vocabolario dal tokenizer
2. Si ricostruisce la mappatura byte-to-unicode di GPT-2
3. Si traduce ogni stringa di token tramite la mappatura inversa
4. Si conservano solo le rappresentazioni testuali UTF-8 valide

## Scelte di Design

### Perché il Decoding Vincolato?

Gli approcci basati solo su prompt con gli LLM raggiungono appena ~30% di affidabilità per output
strutturati. Il decoding vincolato garantisce la validità per costruzione, non per probabilità.

### Livello di Token vs. Livello di Carattere

Lavorare a livello di token (invece che di carattere) offre:
- Generazione più veloce (meno iterazioni)
- Coerenza migliore (unità subword)
- Integrazione con il vocabolario nativo del modello

### Strategia di Mappatura del Vocabolario

Il progetto reimplementa in locale la mappatura BPE byte-level di GPT-2 per evitare di importare
la libreria `tiktoken`, mantenendo le dipendenze al minimo.

## Analisi delle Prestazioni

### Accuratezza

- Selezione della funzione: 100% (funzione corretta identificata per tutti i prompt di test)
- Estrazione degli argomenti: 90%+ (tutti gli argomenti combaciano con i tipi attesi)

### Velocità

- Funzioni semplici: <1s per prompt
- Pattern regex complessi: 5-40s per prompt
- Tempo totale per 11 casi di test: ~80s

### Affidabilità

- JSON valido: 100% (ogni output è parsabile)
- Conformità allo schema: 100% (tutti gli output rispettano le definizioni di funzione)

## Sfide Affrontate

### Generazione di Pattern Regex

Le prime versioni si bloccavano in loop quando generavano pattern regex con tante alternative (es.
pattern per vocali `a|e|i|o|u|...`). La soluzione è stata:

1. Rilevare i loop tracciando i suffissi recenti dei token
2. Se lo stesso suffisso compare 3 volte di fila, interrompere il loop
3. Estrarre una stringa valida dal testo accumulato usando delle euristiche

### Gestione degli Escape nelle Stringhe

Le stringhe JSON richiedono una gestione corretta delle sequenze di escape (`\n`, `\t`, `\"`,
ecc.). Il decoder valida le sequenze di escape durante la generazione e le decodifica dopo.

## Strategia di Testing

### Validazione dell'Input

- Test con file JSON validi e non validi
- Test con file mancanti
- Verifica che vengano mostrati messaggi di errore appropriati

### Conformità allo Schema

- Test di tutti i tipi di parametro (number, string, boolean)
- Test di funzioni con più parametri
- Test dei casi limite (numeri grandi, caratteri speciali, stringhe vuote)

### Test End-to-End

- Lancia l'intera pipeline con i prompt di test forniti
- Verifica che l'output rispetti la struttura JSON attesa
- Controlla che i nomi delle funzioni e i tipi degli argomenti siano corretti

## Risorse

- [Modello Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers/)
- [GPT-2 Byte-Pair Encoding](https://huggingface.co/docs/transformers/tokenizer_summary)
- [Decoding Vincolato per Output Strutturato](https://arxiv.org/abs/2109.04335)

## Uso dell'IA

L'IA è stata usata per:
- Capire l'architettura dei transformer e la tokenizzazione
- Fare debug dei casi limite del decoding vincolato
- Rivedere il codice per la conformità a PEP 8
- Spiegare le tecniche di validazione della grammatica JSON
