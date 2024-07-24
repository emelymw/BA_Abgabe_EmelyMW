Dieses Readme ist eine kurze Anleitung zum Starten der Anwendung.
Für die Nutzung wird eine Neo4j Graphdatenbank Instanz benötigt.

# Neo4j Datenbank
Am einfachsten ist diese neo4j Datenbank in einem Docker Container zu starten.
Dazu wird auf dem lokalen Gerät Docker benötigt. Dazu gibt es [hier](https://docs.docker.com/get-docker/) eine Anleitung.

Das Docker Image für neo4j ist ein offizell bereitgestelltes Image unter dem [Link](https://hub.docker.com/_/neo4j).
Zum Starten eines Docker Containers mit diesem Image kann entweder Docker Desktop oder die Konsole verwendet werden.

## Docker Desktop
Mit der Suchleite kann nach dem neo4j Image gesucht werden und diesesn anschließend mit einem Klick auf RUN geöffnet werden. Es öffnet sich ein Pop-up Fenster für Einstellungen.
Hier zu beachten ist die rechts vorgeschlagen Ports ```(7473, 7474, 7687)``` zu nutzen, zusätzlich muss unter den Eviroment variables die Varaible ```NEO4J_AUTH``` mit dem Wert ```none``` hinzugefügt werden.
Das ist wichtig da der python Treiber auf dem Port 7687 zugreift und keine Anmeldedaten übergeben werden.

## Konsole
Die exakten Befehle zum Starten des Containers über die Konsole ist der [Dokumentation](https://neo4j.com/docs/operations-manual/current/docker/introduction/#docker-image) zu entnehmen. 
Prinzipiel ist es auch hier wichtig die Standard-Ports auf ```(7473, 7474, 7687)``` zu setzen und die Anmeldung auszuschlaten mit ```--env NEO4J_AUTH=none```.

docker run --restart always --publish=7474:7474 --publish=7687:7687 --publish=7473:7473 neo4j:latest --env NEO4J_AUTH=none

# Flask Webserver
Ist die Datenbank gestartet kann die Anwendung genutzt werden.

## Installieren
Dazu müssen zuerste einmal alle benötigen Pip-Paket mit dem Befehl
```
pip install -r requirements.txt
```
installiert werden.

## Starten
Anschließend kann mit dem Befehl
```
flask --app webapplication run
```
die Webanwendung gestartet werden.

# Nutzung
## Starten
docker-compose up


## Webanwendung:
Unter der Adresse
```
http://127.0.0.1:5000/
```
ist sie anschließend erreichbar.
## Neo4j Webanwendung:
Unter der Adresse
```
http://localhost:7474/
```
ist die graphsiche Oberfläche von neo4j zu finden. Dort kann mit dem Befehl ```MATCH (n) RETURN n``` der gesamte Inhalt der Datenbank angezeigt werden.
