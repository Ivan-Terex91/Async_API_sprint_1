# Format code
.PHONY: fmt
fmt:
	black .
	isort .


# Create es indexes
.PHONY: es-create-indexes, es-create-movies-index, es-create-genres-index, es-create-persons-index
es-create-indexes: es-create-movies-index es-create-genres-index es-create-persons-index

es-create-movies-index:
	curl -XPUT localhost:9200/movies -H 'Content-Type: application/json' -d @indexes/movies.json

es-create-genres-index:
	curl -XPUT localhost:9200/genres -H 'Content-Type: application/json' -d @indexes/genres.json

es-create-persons-index:
	curl -XPUT localhost:9200/persons -H 'Content-Type: application/json' -d @indexes/persons.json


# Delete es indexes
.PHONY: es-delete-indexes, es-delete-movies-index, es-delete-genres-index, es-delete-persons-index
es-delete-indexes: es-delete-movies-index es-delete-genres-index es-delete-persons-index

es-delete-movies-index:
	curl -XDELETE localhost:9200/movies

es-delete-genres-index:
	curl -XDELETE localhost:9200/genres

es-delete-persons-index:
	curl -XDELETE localhost:9200/persons
