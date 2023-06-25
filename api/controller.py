from . import models
import pandas as pd
from flask import Flask, make_response,request
from sqlalchemy import create_engine, text
import requests
import base64
import json
from imagekitio import ImageKit
from PIL import Image
from io import BytesIO
import string    
from datetime import datetime, date
import uuid
import datetime
from collections import OrderedDict

def upload_image_cloud(image_base64):
    '''
    Function in charge of uploading an image to imagekit.io, a private cloud, returning
    the url of the image stored in this cloud.

    Args:
        image_url(string): URL of the image to be uploaded
    '''
    with open("passw.json", 'r') as file:
        content = file.read()
        data = json.loads(content)
        

    imagekit = ImageKit(
        public_key=data["imagekit"]["public_key"],
        private_key=data["imagekit"]["private_key"],
        url_endpoint = data["imagekit"]["url_endpoint"]
    )

    # with open(image_url, mode="rb") as img:
    #     imgstr = base64.b64encode(img.read())

    print("Uploading image to Imagekit...")

    # upload an image
    upload_info = imagekit.upload(file=image_base64, file_name="my_file_name.jpg")
    
    print(f"Image {upload_info.file_id} succesfully uploaded to Imagekit.\n")

    return upload_info


def get_image_tags(upload_info, min_confidence=80):
    '''
    Function which uploads an image to Imagga to analyze it by using AI and returning
    tags and the corresponding confidence ratio.

    Args:
        image_cloud_url(string): URL of the image in Imagekit
    '''
    with open("passw.json", 'r') as file:
        content = file.read()
        data = json.loads(content)
        

    api_key = data["imagga"]["api_key"]
    api_secret = data["imagga"]["api_secret"]
    
    print(f"Processing image in {upload_info.file_id} in Imagga...")
    response = requests.get(f"https://api.imagga.com/v2/tags?image_url={upload_info.url}", auth=(api_key, api_secret))
    tags = [
        {
            "tag": t["tag"]["en"],
            "confidence": t["confidence"]
        }
        for t in response.json()["result"]["tags"]
        if t["confidence"] > min_confidence
    ]

    print(f"Tags succesfully generated with a confidence higher than {min_confidence}: {tags}\n")

    return tags


def delete_image_cloud(file_id):
    '''
    Function to delete an image in Imagekit.

    Args:
        file_id(string): Id of the file to eliminate 
    '''

    with open("passw.json", 'r') as file:
        content = file.read()
        data = json.loads(content)
        

    imagekit = ImageKit(
        public_key=data["imagekit"]["public_key"],
        private_key=data["imagekit"]["private_key"],
        url_endpoint = data["imagekit"]["url_endpoint"]
    )

    # delete an image
    delete = imagekit.delete_file(file_id=file_id)

    print(f"Image {file_id} succesfully deleted.\n")

    return None


def save_bin_image_folder(image_base64):
    """
    Function which saves the image analyzed in Imagga in the volume in the folder created for this purpose.

    Args:
        image_base64 (string): Image in base64 to be saved in the docker volume.
    
    Output:
        image_uuid (string): ID of the image
    """

    # Create an image object from the base64 encoded data
    image_data = BytesIO(base64.b64decode(image_base64))
    image = Image.open(image_data)
    image_uuid = str(uuid.uuid4())
    print(f"Saving the image {image_uuid}...")
    # Save the image as a JPG file in the specified folder
    save_path = f"/app/images_db/{image_uuid}.jpg" 
    image.save(save_path, "JPEG")

    print(f"Image {image_uuid} succesfully saved in {save_path}.")
    return image_uuid


# Definition of the input to be included in the table pictures.
def add_row_pictures(image_uuid, image_date, engine): 
    ''' 
    Function which append a new row to the table "pictures".

    Args:
        image_uuid(str): ID of the image
        image_date(str): Date the data of the image
                         was append to the table
        engine: Engine created to connect to the database
    
    Output:
        None
    '''   
    pictures_json = {
        "id":image_uuid,
        "path":f"/app/images_db/{image_uuid}.jpg",
        "date":image_date
    }
    df_pictures = pd.DataFrame([pictures_json])

    print("Appending the new row to the table 'pictures'...")
    df_pictures.to_sql(name='pictures', con=engine, if_exists='append', index=False)
    print("New row succesfully appended to the table 'pictures'.")
    return None


def add_row_tags(tags, image_uuid, image_date, engine): 
    ''' 
    Function which append a new row to the table "pictures".

    Args:
        tags(list): List of dictionaries with the tags and confidence of each of those tags.
        image_uuid(str): ID of the image
        image_date(str): Date the data of the image
                         was append to the table
        engine: Engine created to connect to the database
    
    Output:
        None
    '''    
    if tags:  
        df_tags = (
            pd.DataFrame.from_records(tags)
            .assign(
                picture_id = image_uuid
            )
            .assign(
                date = image_date
            )
            [["tag", "picture_id","confidence","date"]]
        )
        print("Appending the new row to the table 'tags'...")
        df_tags.to_sql(name='tags',
                        con=engine,
                        if_exists='append',
                        index=False)
    
    else:
        json_tags = {
            "tag":"No tags",
            "picture_id":image_uuid,
            "confidence":0,
            "date":image_date
        }

        df_tags = (
            pd.DataFrame([json_tags])
        )

        df_tags.to_sql(name='tags',
                        con=engine,
                        if_exists='append',
                        index=False)

    print("New row succesfully appended to the table 'tag'.")
    return None


def create_image_date():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_image_size_base64(image_base64):
    return f"{round(len(base64.b64decode(image_base64))/1024, 2)}KB"


def select_or_create_database():
    """ 
    Select the Pictures or create it in case it does not exist yet.
    
    Args:
        None
    
    Return:
        engine
    """
    # Connect to the MySQL server
    engine = create_engine('mysql+pymysql://mbit:mbit@db:3306')

    # Create the 'Pictures' database if it doesn't exist
    with engine.begin() as connection:
        # Create a DDL statement to create the database
        create_db_statement = text('CREATE DATABASE IF NOT EXISTS Pictures')

        # Execute the DDL statement
        connection.execute(create_db_statement)

    # Connect to the 'Pictures' database
    engine = create_engine('mysql+pymysql://mbit:mbit@db:3306/Pictures')

    # Execute SQL statements
    with engine.begin() as connection:
        # Create 'pictures' table
        create_pictures_table = text(models.query_create_table_pictures)
        connection.execute(create_pictures_table)

        # Create 'tags' table
        create_tags_table = text(models.query_create_table_tags)
        connection.execute(create_tags_table)
    
    return engine


# Calculo de las tags asociadas a una imagen
def get_image_date (image_id, engine):
    """
    Function in charge of extracting the tags related to one image_id.

    Args:
        image_id(string): string which identifies the image in the database
        engine: engine to connect to the SQL database
    
    Return:
        list_tags(list): List of dictionaries with the tags and their correspondent confidence ratio
    """
    engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")
    query = models.query_select_all_tags

    df_tags_image = (
        pd.read_sql_query(query, con=engine)
        .groupby(["picture_id", "tag", "confidence", "date"]).count()
        .loc[image_id]
        .reset_index()
    )

    return df_tags_image["date"].loc[0]


def get_image_size(image_id, engine):
    """
    Function in charge of calculating the size of a determined image.

    Args:
        image_id(string): string which identifies the image in the database
        engine: engine to connect to the SQL database
    
    Return:
        Image size in KB
    """
    engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")
    query = models.query_select_all_pictures
    df_pictures = pd.read_sql_query(query, con=engine)
    file_path = (
        df_pictures
        .loc[df_pictures["id"]==image_id]
        ["path"]
        .values[0]
    )
    try:
        with open(file_path, "rb") as file:
            image_bin = file.read()

        image_base64 = (
            base64.b64encode(image_bin)
            .decode()
        )

        image_size = f"{round(len(base64.b64decode(image_base64))/1024, 2)}KB"

        return image_size
    
    except:
        return "Information not available"


# Calculo de las tags asociadas a una imagen
def get_image_tags (image_id, engine):
    """
    Function in charge of extracting the tags related to one image_id.

    Args:
        image_id(string): string which identifies the image in the database
        engine: engine to connect to the SQL database
    
    Return:
        list_tags(list): List of dictionaries with the tags and their correspondent confidence ratio
    """
    engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")
    query = models.query_select_all_tags

    df_tags_image = (
        pd.read_sql_query(query, con=engine)
        .groupby(["picture_id", "tag", "confidence", "date"]).count()
        .loc[image_id]
        .reset_index()
    )

    list_tags = []
    for index, row in df_tags_image.iterrows():
        test_image_dict = {
            "tag":row["tag"],
            "confidence":row["confidence"]
        }
        list_tags.append(test_image_dict)
    return list_tags


app = Flask(__name__)

@app.get("/get_images")
def get_images():    
    engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")

    min_date = date.fromisoformat(request.args.get("min_date", '1000-01-01'))
    max_date = date.fromisoformat(request.args.get("max_date", '9999-12-31'))

    # # Convert string dates to datetime objects
    min_date_str = min_date.isoformat()
    max_date_str = max_date.isoformat()

    # min_date = '2023-05-12'
    # max_date = '2023-06-21'

    tags_string = request.args.get("tags_list"," ")

    if tags_string != " ":
        tags_list = tags_string.split(",")

    else:
        query = models.query_select_all_tags

        tags_list = (
            pd.read_sql_query(query, con=engine)
            ['tag']
            .drop_duplicates()
            .to_list()
            )
    print(f"Extracting data considering the tags {tags_list} between {min_date} and {max_date}...")

    query = f"""SELECT  id, 
                        path, 
                        CAST(date AS date) AS dates
                FROM pictures
                WHERE date BETWEEN '{min_date_str}' AND '{max_date_str}'"""

    df_pictures = pd.read_sql_query(query, con=engine)

    df_tags_filtered = pd.DataFrame()
    for tag in tags_list:
        query = f"""SELECT * 
                FROM tags
                WHERE tag = '{tag}'
                ORDER BY picture_id"""
        df_tags_filtered = pd.concat([df_tags_filtered, pd.read_sql_query(query, con=engine)],
                            axis=0)
    df_tags_filtered = df_tags_filtered.reset_index(drop = True)

    df_tags_filtered[df_tags_filtered["tag"]==len(tags_list)]["picture_id"].tolist()
    df_tag_pictures = (
        df_tags_filtered
        .merge(df_pictures, how = "inner",
                    left_on="picture_id",
                    right_on="id")
        [['id','tag','confidence','date','path']]
        .sort_values(by="id")    
    )

    df_tag_pictures = (
        df_tag_pictures
        .groupby("id")
        .count()
        [["tag"]]
        .reset_index()
    )

    list_images_filtered = (
        df_tag_pictures
        [df_tag_pictures["tag"]==len(tags_list)]
        ["id"]
        .to_list()
    )
    list_images_filtered

    output_images_list = []
    for image_id in list_images_filtered:
        print(f"Extracting informacion from {image_id}...")
        image_size = get_image_size(image_id=image_id, engine=engine)
        image_date = get_image_date (image_id=image_id, engine=engine)
        image_tags = get_image_tags(image_id, engine=engine)

        output_images_list_partial = {
            "id":image_id,
            "size":image_size,
            "date":image_date,
            "tags":image_tags
        }
        # print(output_images_list_partial)
        output_images_list.append(output_images_list_partial)
        print(f"{output_images_list_partial}\n")

    return output_images_list


def tags_list_def(tags_string):
    engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")
    if tags_string != " ":
        tags_list = tags_string.split(",")

    else:
        query = models.query_select_all_tags

        tags_list = (
            pd.read_sql_query(query, con=engine)
            ['tag']
            .drop_duplicates()
            .to_list()
            )
    return tags_list


def images_id_filter(min_date_str, max_date_str, tags_list):
    engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")
    query = f"""SELECT  id, 
                path, 
                CAST(date AS date) AS dates
                FROM pictures
                WHERE date BETWEEN '{min_date_str}' AND '{max_date_str}'"""

    df_pictures = pd.read_sql_query(query, con=engine)

    df_tags_filtered = pd.DataFrame()
    for tag in tags_list:
        query = f"""SELECT * 
                FROM tags
                WHERE tag = '{tag}'
                ORDER BY picture_id"""
        df_tags_filtered = pd.concat([df_tags_filtered, pd.read_sql_query(query, con=engine)],
                            axis=0)
    df_tags_filtered = df_tags_filtered.reset_index(drop = True)

    df_tags_filtered[df_tags_filtered["tag"]==len(tags_list)]["picture_id"].tolist()
    df_tag_pictures = (
        df_tags_filtered
        .merge(df_pictures, how = "inner",
                    left_on="picture_id",
                    right_on="id")
        [['id','tag','confidence','date','path']]
        .sort_values(by="id")    
    )

    df_tag_pictures = (
        df_tag_pictures
        .groupby("id")
        .count()
        [["tag"]]
        .reset_index()
    )

    list_images_filtered = (
        df_tag_pictures
        [df_tag_pictures["tag"]==len(tags_list)]
        ["id"]
        .to_list()
    )
    return list_images_filtered


def get_output_images_list(list_images_filtered):
    
    output_images_list = []
    for image_id in list_images_filtered:
        engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")
        print(f"Extracting informacion from {image_id}...")
        image_size = get_image_size(image_id=image_id, engine=engine)
        image_date = get_image_date (image_id=image_id, engine=engine)
        image_tags = get_image_tags(image_id, engine=engine)

        output_images_list_partial = {
            "id":image_id,
            "size":image_size,
            "date":image_date,
            "tags":image_tags
        }
        # print(output_images_list_partial)
        output_images_list.append(output_images_list_partial)
        print(f"{output_images_list_partial}\n")

    return output_images_list


def download_image_api(image_id, engine):
    """
    Function which downloads and saved a picture based on the image_id.

    Args:
        image_id (string): ID which identifies the picture in the database
    
    Return:
        None
    """
    query = models.query_select_all_pictures
    df_pictures = pd.read_sql_query(query, con=engine)
    file_path = (
        df_pictures
        .loc[df_pictures["id"]==image_id]
        ["path"]
        .values[0]
    )
    print(f"Saving the file {file_path}...")
    try:
        with open(file_path, "rb") as file:
            image_bin = file.read()

        save_path = f"../tmp/{image_id}.jpg" # Sustituir por el volumen
        with open(save_path, "wb") as save_file:
            save_file.write(image_bin)
        
        print(f"File succesfully saved in {save_path}")
    except:
        print("The file could not be saved. There was a problem.")
    return None


def get_image_base64(image_id, engine):
    """
    Function which reads a file and transform it into base64.

    Args:
        image_id (string): ID which identifies the picture in the database
    
    Return:
        None
    """
    query = models.query_select_all_pictures
    df_pictures = pd.read_sql_query(query, con=engine)
    file_path = (
        df_pictures
        .loc[df_pictures["id"]==image_id]
        ["path"]
        .values[0]
    )
    try:
        with open(file_path, "rb") as file:
            image_bin = file.read()

        image_base64 = (
            base64.b64encode(image_bin)
            .decode()
        )
        return image_base64

    except:
        print("Image not available")
        return None


def get_tags_info(engine, min_date_str, max_date_str):
    """
    Get tags info from the database
    
    Args:
        min_date_str (str): min date to filter
        max_date_str (str): max date to filter
    
    Return:
        tag_list (list): list with all required outputs of the API endpoint
    """
    query = f"""SELECT  tag, 
                    picture_id,
                    confidence,
                    CAST(date AS date) AS dates
            FROM tags
            WHERE date BETWEEN '{min_date_str}' AND '{max_date_str}'"""

    tag_list = []
    df_pictures = pd.read_sql_query(query, con=engine)
    print(df_pictures)
    for tag in list(df_pictures.tag.unique()):
        df_picture_tags = (
            df_pictures
            .groupby(["tag", "picture_id", "confidence", "dates"])
            .count()
            .loc[tag]
            .reset_index()
        )
        n_images = int(df_picture_tags.size / len(df_picture_tags.columns))
        min_confidence = df_picture_tags.confidence.min()
        max_confidence = df_picture_tags.confidence.max()
        mean_confidence = df_picture_tags.confidence.mean()
        tag_info = {
            "tag": tag,
            "n_images": n_images,
            "min_confidence": min_confidence,
            "max_confidence": max_confidence,
            "mean_confidence": mean_confidence
        }
        tag_list.append(tag_info)
    return tag_list



