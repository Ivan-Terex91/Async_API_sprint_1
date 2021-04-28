select_modified_filmworks_from_persons = """
SELECT fw_p.filmwork_id
  FROM movies_person p
  JOIN movies_filmwork_participants fw_p
    ON p.id = fw_p.person_id
 WHERE p.modified > {last_timestamp}
 ORDER BY p.modified ASC
OFFSET {offset}
 LIMIT {limit}
"""


select_modified_filmworks_from_genres = """
SELECT fw_g.filmwork_id
  FROM movies_genre g
  JOIN movies_filmwork_genres fw_g
    ON g.id = fw_g.genre_id
 WHERE g.modified > {last_timestamp}
 ORDER BY g.modified ASC
OFFSET {offset}
 LIMIT {limit}
"""


select_modified_filmworks = """
SELECT id
  FROM movies_filmwork
 WHERE modified > {last_timestamp}
 ORDER BY modified ASC
OFFSET {offset}
 LIMIT {limit}
"""


select_filmworks_query = """
SELECT fw.id,
       fw.filmwork_type,
       fw.title,
       fw.description,
       fw.rating,
       array_agg(g.name)
  FROM movies_filmwork fw
  LEFT JOIN movies_filmwork_genres fw_g
    ON fw.id = fw_g.filmwork_id
  LEFT JOIN movies_genre g
    ON fw_g.genre_id = g.id
 WHERE fw.id in ({filmworks_ids})
 GROUP BY fw.id
 ORDER BY fw.modified ASC
"""


select_filmworks_participants_query = """
SELECT fw_p.filmwork_id,
       p.id,
       p.first_name,
       p.last_name,
       fw_p.role
  FROM movies_person p
  JOIN movies_filmwork_participants fw_p
    ON p.id = fw_p.person_id
 WHERE fw_p.filmwork_id in ({filmworks_ids})
"""


select_filmworks_genres_query = """
SELECT fw_g.filmwork_id,
       g.id,
       g.name
  FROM movies_genre g
  JOIN movies_filmwork_genres fw_g
    ON g.id = fw_g.genre_id
 WHERE fw_g.filmwork_id in ({filmworks_ids})
"""


select_modified_persons = """
SELECT id,
       first_name,
       last_name
  FROM movies_person
 WHERE modified > {last_timestamp}
 ORDER BY modified ASC
OFFSET {offset}
 LIMIT {limit}
"""


select_modified_genres = """
SELECT id,
       name
  FROM movies_genre
 WHERE modified > {last_timestamp}
 ORDER BY modified ASC
OFFSET {offset}
 LIMIT {limit}
"""
