# Vorausetzung
Docker + Docker Compose

# Nutzung
## Starten
docker-compose up

## Webanwendung:
Unter der Adresse
```
http://127.0.0.1:5001/
```
ist sie anschließend erreichbar.
Nach Upload einer YAML oder JSON Datei startet die Verarbeitung.

## Neo4j Webanwendung:
Unter der Adresse
```
http://localhost:7474/
```
ist die graphsiche Oberfläche von neo4j zu finden. Dort kann mit dem Befehl ```MATCH (n) RETURN n``` den gesamte Inhalt der Datenbank angezeigt bekommen.
