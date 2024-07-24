## Vorausetzung
Docker + Docker Compose

## Starten
docker-compose up

## Webanwendung:
Unter der Adresse
```
http://127.0.0.1:5001/
```
ist sie anschließend erreichbar.
Nach Upload einer YAML oder JSON Datei startet die Sequenzgernerierung.

## Neo4j Webanwendung:
Unter der Adresse
```
http://localhost:7474/
```
ist die graphsiche Oberfläche von neo4j zu finden. Dort kann mit dem Befehl ```MATCH (n) RETURN n``` der gesamte Inhalt der Datenbank angezeigt werden.
