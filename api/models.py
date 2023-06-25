query_create_db = 'CREATE DATABASE IF NOT EXISTS Pictures'

query_create_table_pictures = '''
            CREATE TABLE IF NOT EXISTS pictures (
                id VARCHAR(36) PRIMARY KEY,
                path VARCHAR(255) NOT NULL,
                date VARCHAR(255) NOT NULL
            )
        '''

query_create_table_tags = '''
            CREATE TABLE IF NOT EXISTS tags (
                tag VARCHAR(32) NOT NULL,
                picture_id VARCHAR(255) NOT NULL,
                confidence FLOAT,
                date VARCHAR(255) NOT NULL,
                PRIMARY KEY (tag, picture_id),
                FOREIGN KEY (picture_id) REFERENCES pictures(id)
            )
        '''

query_select_all_tags = """ SELECT *
                FROM tags"""

query_select_all_pictures = """ SELECT *
                FROM pictures
    """

# query_filter_min_max_date = f"""SELECT  id, 
#                                         path, 
#                                         CAST(date AS date) AS dates
#                                 FROM pictures
#                                 WHERE date BETWEEN '{min_date_str}' AND '{max_date_str}'"""

# query_filter_tag = f"""SELECT * 
#                 FROM tags
#                 WHERE tag = '{tag}'
#                 ORDER BY picture_id"""

