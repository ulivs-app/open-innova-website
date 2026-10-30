# Traffico e stime ambientali annuali

## Che cosa possiamo sapere

CloudFront pubblica automaticamente `Requests` e `BytesDownloaded` in CloudWatch,
regione `us-east-1`, namespace `AWS/CloudFront`, dimensioni `DistributionId` e
`Region=Global`. Le metriche standard non richiedono analytics nel browser.

- `Requests`: tutte le richieste HTTP dei visitatori della distribuzione, incluse
  risorse, bot, errori e metodi diversi. Non sono persone, sessioni o pagine lette.
- `BytesDownloaded`: byte scaricati per GET e HEAD. È un punto di partenza più
  pertinente al modello per byte rispetto a richieste × peso medio di una pagina.
- Le metriche aggregate non permettono di ricostruire URL, utenti o distinguere
  completamente i bot. Non includono contenuti riutilizzati dalla cache del browser.
- I log, se già attivi, possono aggiungere dettaglio; abilitarli richiede una scelta
  separata su costi, accessi e conservazione. Non sono stati attivati.

Fonti: [metriche CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/viewing-cloudfront-metrics.html),
[monitoraggio](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/monitoring-using-cloudwatch.html),
[conservazione CloudWatch](https://aws.amazon.com/cloudwatch/faqs/).
La conservazione massima ordinaria arriva a 15 mesi, con aggregazioni meno fini
per i dati più vecchi: esportare almeno una volta l'anno e conservare gli originali.

## Esito della verifica del 30 ottobre 2026

Distribuzione identificata nella configurazione di deploy: `E2IUEDFNFT7LLX`.
Il profilo `open-innova` usa un'utenza di deploy che non autorizza
`cloudwatch:GetMetricStatistics`. La lettura ha restituito `AccessDenied`.
Non è stato ricavato un numero di richieste o byte. Non confondere l'assenza di
accesso con traffico nullo. Nessun permesso o impostazione AWS è stato cambiato.

## Esportare con un'identità autorizzata alla lettura

Esempio per il 2026 completo, da eseguire dopo la fine dell'anno con un profilo
che abbia il permesso `cloudwatch:GetMetricStatistics`:

```bash
aws --profile PROFILO_LETTURA --region us-east-1 cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront --metric-name Requests \
  --dimensions Name=DistributionId,Value=E2IUEDFNFT7LLX Name=Region,Value=Global \
  --start-time 2026-01-01T00:00:00Z --end-time 2027-01-01T00:00:00Z \
  --period 86400 --statistics Sum --output json > requests-2026.json

aws --profile PROFILO_LETTURA --region us-east-1 cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront --metric-name BytesDownloaded \
  --dimensions Name=DistributionId,Value=E2IUEDFNFT7LLX Name=Region,Value=Global \
  --start-time 2026-01-01T00:00:00Z --end-time 2027-01-01T00:00:00Z \
  --period 86400 --statistics Sum --output json > bytes-2026.json
```

Sommare `Sum`, non le medie. Controllare periodo, giorni coperti, eventuali cambi
di distribuzione e punti mancanti. Un punto mancante non è automaticamente zero.
Se la distribuzione è nata durante l'anno, indicare il periodo operativo effettivo.
Non annualizzare una frazione di anno senza dichiarare l'estrapolazione.

## Acqua: che cosa dire e che cosa calcolare

Possiamo stimare una quota di acqua di raffreddamento attribuita al traffico,
non misurare l'evaporazione causata dal sito. Il WUE descrive consumo idrico per
energia IT e non identifica, da solo, un volume misurato di vapore.

Scenario indicativo, con i coefficienti già usati nel sito:

```
GB = somma BytesDownloaded / 1.000.000.000
energia operativa data center stimata (kWh) = GB × 0,055
acqua di raffreddamento attribuita (L) = GB × 0,055 × WUE
```

Con WUE 1,8 L/kWh si ottengono 0,099 L/GB; con la media AWS Europa 2025 di
0,05 L/kWh, 0,00275 L/GB. Sono due scenari distinti, non gli estremi di un
intervallo di confidenza. Per anni futuri verificare se esiste un WUE pertinente
più aggiornato. La media AWS non misura i nodi CloudFront che servono il sito.

I byte CloudWatch e quelli misurati dallo script hanno confini diversi: il primo
conta traffico CDN aggregato anche automatico; il secondo un insieme di risposte
alle pagine della sitemap, incluse intestazioni. Registrare la differenza e non
presentare il totale annuale come semplice somma delle stime per pagina.

Per un dato reale servirebbero misure del fornitore sul consumo IT e sull'acqua,
relative ai servizi e ai periodi interessati. La linearità del modello è una
regola di attribuzione, non una previsione fisica della crescita dei consumi.

## Confronto con la carta

`data/paper.json` conserva i fattori ufficiali UK 2026 di produzione della carta
(riciclata e vergine), celle sorgente, unità e ipotesi. Un foglio A4 di 80 g/m²
pesa 0,210 × 0,297 × 80 = 4,9896 g. Applicando i fattori di produzione si ottengono
circa 5,2–6,7 g CO₂e per foglio. Il confronto pubblicato è illustrativo e riguarda
questi valori e un caricamento medio della fotografia web datata.

Non stima la stampa effettiva dell'intero sito, né il tempo di lettura digitale.
Per un confronto equivalente occorrerebbe definire lo stesso contenuto e numero
di letture, contare i fogli dopo l'impaginazione e includere carta, stampa,
apparecchiature, energia e fine vita con confini coerenti.
