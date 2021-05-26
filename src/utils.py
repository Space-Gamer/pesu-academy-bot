import os
import json
import asyncio
import asyncpraw
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from gensim.models.doc2vec import TaggedDocument
from nltk.tokenize import word_tokenize
from selenium.webdriver.common.by import By
from pesudb import *
from pydictionary import *
from doc2sim import *
from instagram import *


async def cleanUp():
    files = [fname for fname in os.listdir() if Path(fname).suffix in [
        ".pdf", ".png", ".jpg", ".jpeg"]]
    for fname in files:
        try:
            os.remove(fname)
        except FileNotFoundError:
            pass


async def getDictionaryMeaning(query, n=5):
    flag, word = checkWordExistsInDictionary(query)
    if flag:
        results, antonyms = getRecordsFromDictionary(query, n)
        return True, [results, antonyms]
    else:
        return flag, word


async def searchPESUAcademy(driver, query):
    query = query.upper()

    driver.get("https://www.pesuacademy.com/Academy/")
    class_section_button = driver.find_element_by_xpath(
        r'//*[@id="knowClsSection"]')
    class_section_button.click()

    entry_box = driver.find_element_by_xpath(
        r'//*[@id="knowClsSectionModalLoginId"]')
    await asyncio.sleep(0.4)

    entry_box.send_keys(query)

    search_button = driver.find_element_by_xpath(
        r'//*[@id="knowClsSectionModalSearch"]')
    search_button.click()
    await asyncio.sleep(0.4)

    try:
        _ = driver.find_element_by_xpath(
            r'//*[@id="knowClsSectionModalTableDate"]/tr/td[3]').text
    except:
        return None
    else:
        result = list()
        table = driver.find_element(By.ID, 'knowClsSectionModalTableDate')
        rows = table.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            col = row.find_elements(By.TAG_NAME, "td")
            col = [t.text for t in col]
            result.append(col)
    return result


async def checkMaliciousCode(source_code):
    bad_codes = ["from os", "from subprocess",
                 "import os", "import subprocess"]
    for code_segment in bad_codes:
        if code_segment in source_code:
            return True
    return False


async def getPESUDBResults(query):
    query = query.upper()
    filters = query.split("&")
    base_url = "https://pesu-db.herokuapp.com"
    for f in filters:
        f = f.lower().strip()
        f = f.replace(" ", "%20")
        base_url += "/" + f
    listResult, truncated = searchPESUDatabase(filters)
    return listResult, truncated, base_url


async def shortenLinkBitly(long_url, BITLY_TOKEN, BITLY_GUID):
    headers = {
        'Authorization': f'Bearer {BITLY_TOKEN}',
        'Content-Type': 'application/json',
    }
    data = {"long_url": f"{long_url}", "group_guid": f"{BITLY_GUID}"}
    data = json.dumps(data)
    response = requests.post(
        'https://api-ssl.bitly.com/v4/shorten', headers=headers, data=data)
    short_url = response.json()["link"]
    return short_url, response


async def shortenLinkLongRip(chrome, long_url):
    chrome.get("http://www.long.rip/")
    await asyncio.sleep(1)

    url_box = chrome.find_element_by_xpath(r'//*[@name="url"]')
    url_box.send_keys(long_url)
    await asyncio.sleep(0.3)

    button = chrome.find_element_by_xpath(
        r'//*[@class="get-started-btn mx-auto"]')
    button.click()
    await asyncio.sleep(1)

    result_box = chrome.find_element_by_xpath(r'//*[@id="custom_a"]')
    return result_box.text


async def shortenLinkRedirector(short_url, long_url):
    data = {
        "source_url": long_url,
        "alias_url": short_url
    }

    response = requests.post(
        "https://goto-link.herokuapp.com/register", data=data)

    return response


async def generateSpongebobMeme(query):
    captions = query.split('&')
    if len(captions) == 1:
        top = None
        bottom = captions[0].strip()
    else:
        top, bottom = captions[:2]
        top = top.strip()
        bottom = bottom.strip()

    base_url = "https://spongebob-service.herokuapp.com/"
    if top == None:
        meme_url = f"https://spongebob-service.herokuapp.com/{bottom}"
    else:
        meme_url = f"https://spongebob-service.herokuapp.com/{top}/{bottom}"

    response = requests.get(meme_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    img_tags = soup.find_all('img')
    img_url = img_tags[0]["src"]
    img_url = base_url + img_url
    response = requests.get(img_url)
    with open("meme.jpg", 'wb') as outfile:
        outfile.write(response.content)


async def getPESUAnnouncements(chrome, username, password):
    chrome.get("https://pesuacademy.com/Academy")
    await asyncio.sleep(2)

    username_box = chrome.find_element_by_xpath(r'//*[@id="j_scriptusername"]')
    password_box = chrome.find_element_by_xpath(r'//*[@name="j_password"]')

    username_box.send_keys(username)
    await asyncio.sleep(0.3)
    password_box.send_keys(password)
    await asyncio.sleep(0.3)

    sign_in_button = chrome.find_element_by_xpath(
        r'//*[@id="postloginform#/Academy/j_spring_security_check"]')
    sign_in_button.click()
    await asyncio.sleep(1)

    menu_options = chrome.find_elements_by_xpath(r'//*[@class="menu-name"]')
    menu_options[8].click()
    await asyncio.sleep(1)

    announcement_boxes = chrome.find_elements_by_xpath(
        r'//*[@class="elem-info-wrapper"]')
    announcement_boxes.extend(chrome.find_elements_by_xpath(
        r'//*[@class="elem-info-wrapper  "]'))

    data = list()
    for a_box in announcement_boxes:
        header_box = a_box.find_element_by_xpath(r'.//*[@class="text-info"]')
        header = header_box.text

        date_box = a_box.find_element_by_xpath(
            r'.//*[@class="text-muted text-date pull-right"]')
        date = datetime.strptime(date_box.text, "%d-%B-%Y").date()

        bodies = a_box.find_elements_by_xpath(r'.//*[@class="col-md-12"]')
        all_attachments = list()
        if not bodies:
            bodies = a_box.find_elements_by_xpath(r'.//*[@class="col-md-8"]')
        for b in bodies:
            paragraphs = b.find_elements_by_tag_name("p")
            attachments = b.find_elements_by_xpath(
                r'.//*[@class="pesu-ico-download"]')
            attachment_names = b.find_elements_by_tag_name("a")
            if paragraphs:
                content = '\n'.join([p.text for p in paragraphs])
            if attachments:
                attachment_names = [
                    a_name.text for a_name in attachment_names if a_name.text != "Read more"]
                all_attachments.extend(attachment_names)
                for a in attachments:
                    a.click()

        img_base64 = None
        img_box = a_box.find_elements_by_xpath(
            r'.//*[@class="img-responsive"]')
        if img_box:
            img_base64 = img_box[0].get_attribute("src")

        temp = {
            "date": date,
            "header": header,
            "body": content,
            "img": img_base64,
            "attachments": all_attachments
        }

        data.append(temp)

    return data


async def getDocumentSimilarity(filenames, model_type="doc2vec", phrase=True):
    if model_type == "doc2vec":
        documents = list(map(getText, filenames))
        if phrase:
            documents = list(map(phraseTransform, documents))
        documents = [" ".join(d) for d in documents]
        document_words = list(map(word_tokenize, documents))

        train_text = [
            TaggedDocument(
                words=w,
                tags=[str(i)]
            ) for i, w in enumerate(document_words)
        ]

        test_text = document_words
        total_files = len(filenames)
        result = list()
        similarity_matrix = np.identity(total_files, dtype=float)

        for i in range(total_files):
            for j in range(total_files):
                if i != j and similarity_matrix[i, j] == 0:
                    model = createDoc2VecModel(
                        [train_text[i]] + [train_text[j]])
                    vecs = list(map(model.infer_vector, [
                                test_text[i]] + [test_text[j]]))
                    similarity_matrix[i, j] = cosineSimilarity(
                        vecs[0], vecs[1])
                    similarity_matrix[j, i] = similarity_matrix[i, j]
                    result.append(
                        (filenames[i], filenames[j], similarity_matrix[i, j]))
                    del model

        return result


async def getRedditPosts(REDDIT_PERSONAL_USE_TOKEN, REDDIT_SECRET_TOKEN, REDDIT_USER_AGENT, n=5):
    reddit = asyncpraw.Reddit(client_id=REDDIT_PERSONAL_USE_TOKEN,
                              client_secret=REDDIT_SECRET_TOKEN, user_agent=REDDIT_USER_AGENT)

    new_posts = await reddit.subreddit('PESU', fetch=True)
    data = list()

    async for post in new_posts.new(limit=n):
        post_data = dict()
        post_data["title"] = post.title
        post_data["content"] = post.selftext
        post_data["url"] = f"https://reddit.com{post.permalink}"
        post_data["create_time"] = datetime.fromtimestamp(post.created)
        post_data["author"] = post.author.name
        post_data["images"] = list()

        if "media_metadata" in post.__dict__:
            image_details = post.media_metadata
            if image_details:
                for key in image_details:
                    if image_details[key]['e'] == "Image":
                        post_data["images"].append(
                            image_details[key]['p'][-1]['u'])
        elif "preview" in post.__dict__:
            if post.preview["images"]:
                for i in post.preview["images"]:
                    post_data["images"].append(i["resolutions"][-1]["url"])

        data.append(post_data)

    return data
