*This project has been created as part of the 42 curriculum by tcostant.*

## Description

Un sistema RAG (Retrieval Augmented Generation) per permettere a un modello AI (Qwen3-0.6B) di rispondere in modo
accurato rispetto a informazioni contenute in un grande corpo di dati come la libreria vLLM.

3 fasi:
 1-> chunking e indexing: rompere il corpo di tutta la libreria vLLM in chunk di 2000      
 caratteri max e poi ordinarli in ordine alfanumerico(regole ast per python e # per .md)   
                                                                                           
 2->retrieval con bm25: do uno score bm25 con la libreria BM250kpapi e scelgo i k chunk    
 con score piu' alto                                                                       
                                                                                           
 3-> augmented generation: do i k chunk in pasto a qwen come contesto e gli faccio         
 generare una risposta
