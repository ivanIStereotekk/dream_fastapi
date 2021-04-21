import numpy as np
import logging
import os
import re
import random
from enum import Enum, auto

import sentry_sdk
import requests

import dialogflows.scopes as scopes
from CoBotQA.cobotqa_service import send_cobotqa
import common.dialogflow_framework.stdm.dialogflow_extention as dialogflow_extention
import common.dialogflow_framework.utils.state as state_utils
from common.universal_templates import if_chat_about_particular_topic
from common.universal_templates import COMPILE_NOT_WANT_TO_TALK_ABOUT_IT
from common.constants import CAN_CONTINUE_SCENARIO, MUST_CONTINUE, CAN_NOT_CONTINUE, CAN_CONTINUE_SCENARIO_DONE
import common.greeting as common_greeting
import common.link as common_link
from common.sport import (
    BINARY_QUESTION_ABOUT_SPORT,
    BINARY_QUESTION_ABOUT_ATHLETE,
    BINARY_QUESTION_ABOUT_COMP,
    OFFER_FACT_COMPETITION,
    OPINION_REQUESTS,
    OPINION_ABOUT_ATHLETE_WITH_TEAM,
    OPINION_ABOUT_ATHLETE_WITH_TEAM_AND_POS,
    OPINION_ABOUT_ATHLETE_WITHOUT_TEAM,
    OPINION_ABOUT_TEAM,
    SPORT_TEMPLATE,
    KIND_OF_SPORTS_TEMPLATE,
    KIND_OF_COMPETITION_TEMPLATE,
    ATHLETE_TEMPLETE,
    SUPPORT_TEMPLATE,
    QUESTION_TEMPLATE,
    LAST_CHANCE_TEMPLATE,
    COMPETITION_TEMPLATE,
    ASK_ABOUT_ATH_IN_KIND_OF_SPORT,
    SUPER_CONFIDENCE,
    HIGH_CONFIDENCE,
    ZERO_CONFIDENCE,
    NUMBER_PROBABILITY
)

import common.dialogflow_framework.utils.condition as condition_utils
from common.utils import get_sentiment, get_named_persons


sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"))


MASKED_LM_SERVICE_URL = os.getenv("MASKED_LM_SERVICE_URL")

logger = logging.getLogger(__name__)


class State(Enum):
    SYS_LINK_TO_LIKE_SPORT = auto()
    SYS_LINK_TO_LIKE_ATHLETE = auto()
    SYS_LINK_TO_LIKE_COMP = auto()
    USR_START = auto()

    SYS_WHO_FAVORITE_ATHLETE = auto()
    SYS_LETS_TALK_ATHLETE = auto()
    USR_ASK_ABOUT_ATHLETE = auto()

    SYS_WHO_SUPPORT = auto()
    USR_ASK_WHO_SUPPORT = auto()

    SYS_LETS_TALK_SPORT = auto()
    SYS_WHAT_SPORT = auto()
    USR_ASK_ABOUT_SPORT = auto()

    SYS_TELL_ATHLETE = auto()
    USR_LIKE_ATHLETE = auto()

    SYS_TELL_SPORT = auto()
    USR_WHY_LIKE_SPORT = auto()

    SYS_LETS_TALK_ABOUT_COMP = auto()
    SYS_ASK_ABOUT_COMP = auto()
    USR_ASK_ABOUT_COMP = auto()

    SYS_TELL_COMP = auto()
    USR_WHY_LIKE_COMP = auto()

    SYS_TELL_NEGATIVE = auto()
    USR_TELL_NEGATIVE = auto()

    SYS_NOT_NEGATIVE_AFTER_Y_COMP = auto()
    USR_OFFER_FACT_ABOUT_COMP = auto()
    USR_GET_FACT_ABOUT_COMP = auto()
    SYS_WANT_FACT_ABOUT_COMP = auto

    SYS_NOT_NEGATIVE_AFTER_Y_KIND_OF_SPORT = auto()
    USR_HAVE_ATH_FROM_THIS_SPORT = auto()
    SYS_TELL_TEAM = auto()
    SYS_TELL_ATHLETE_WITHOUT_TEAM = auto()

    SYS_NOT_NEG_AFTER_ATHLETE_WITH_TEAM = auto()
    USR_LINK_TO_TRAVEL = auto()
    USR_GET_OPIN_ABOUT_TEAM = auto()
    SYS_NOT_NEG_AFT_COMMENT_TEAM = auto()

    SYS_LAST_CHANCE = auto()
    USR_LAST_CHANCE = auto()
    SYS_ERR = auto()


##################################################################################################################
# Init DialogFlow
##################################################################################################################


simplified_dialogflow = dialogflow_extention.DFEasyFilling(State.USR_START)


##################################################################################################################
##################################################################################################################
# Design DialogFlow.
##################################################################################################################
##################################################################################################################


##################################################################################################################
# HELP FUNCTION
##################################################################################################################


def donot_chat_about(uttr):
    flag = bool(re.search(COMPILE_NOT_WANT_TO_TALK_ABOUT_IT, uttr["text"].lower()))
    return flag


def not_negative_emotion(vars):
    dont_chat = donot_chat_about(state_utils.get_last_human_utterance(vars))
    it_is_not_negative = "negative" not in get_sentiment(state_utils.get_last_human_utterance(vars), probs=False,
                                                         default_labels=["neutral"])
    user_positive_or_neutral = it_is_not_negative and not dont_chat
    user_agrees = condition_utils.is_yes_vars(vars)
    return user_agrees or user_positive_or_neutral


def compose_topic_offering(excluded_skills=None):
    excluded_skills = [] if excluded_skills is None else excluded_skills
    ask_about_topic = random.choice(common_greeting.GREETING_QUESTIONS["what_to_talk_about"])
    offer_topics_template = random.choice(common_greeting.TOPIC_OFFERING_TEMPLATES)

    available_topics = [topic for skill_name, topic in common_link.LIST_OF_SCRIPTED_TOPICS.items()
                        if skill_name not in excluded_skills]

    topics = np.random.choice(available_topics, size=2, replace=False)
    offer_topics = offer_topics_template.replace("TOPIC1", topics[0]).replace("TOPIC2", topics[1])

    response = f"{ask_about_topic} {offer_topics}"
    return response


def get_news_for_person_or_org(vars):
    array_person = get_named_persons(state_utils.get_last_human_utterance(vars))
    array_org = get_org_in_last_human_utterance(vars)
    person_or_org_array = array_person + array_org
    if person_or_org_array:
        news_string = get_news(person_or_org_array[-1])
        flag = True
    else:
        news_string = f""
        flag = False
    return flag, news_string


def get_news(string):
    try:
        keys = [
            f"188eea501739478981eebf0b44695e75",
            f"1fd88e76511f4ff19ad7a2a9ee84826c",
            f"ee51596f8c3545f3aa382932844a15a8",
            f"7e38f3aeae164d59a05d9874dc0db852",
        ]
        string_for_request = string.replace(" ", "%20")
        link = f"http://newsapi.org/v2/everything?q={string_for_request}&apiKey={random.choice(keys)}"
        news = requests.get(link, timeout=0.5)
        news_json = news.json()["articles"]
        title = news_json[0]["title"]
        news_string = f"I recently read the news that {title}. What do you think about this?"
        return news_string
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.exception(e)
        return f""


def get_org_in_last_human_utterance(vars):
    user_mentioned_named_entities = state_utils.get_named_entities_from_human_utterance(vars)
    user_mentioned_name = []
    for named_entity in user_mentioned_named_entities:
        if named_entity["type"] == "ORG":
            user_mentioned_name.append(named_entity["text"])
    return user_mentioned_name


def entity_in_last_uttr_from_sport_area(vars):
    array_person = get_named_persons(state_utils.get_last_human_utterance(vars))
    array_org = get_org_in_last_human_utterance(vars)
    array_entities = array_person + array_org
    annotated_utterance = state_utils.get_last_human_utterance(vars)
    array_sport_entities = []
    for entity in array_entities:
        wiki_parser_for_entity = annotated_utterance["annotations"].get("wiki_parser", {}).get(
            "topic_skill_entities_info", {}).get(entity.lower(), {})
        if bool(wiki_parser_for_entity) is False:
            wiki_parser_for_entity = annotated_utterance["annotations"].get("wiki_parser", {}).get(
                "entities_info", {}).get(entity.lower(), {})
        kind_of_sport = wiki_parser_for_entity.get("sport", [["", ""]])[-1][1]
        occupation = wiki_parser_for_entity.get("occupation", [["", ""]])[-1][1]
        instance_of = wiki_parser_for_entity.get("instance of", [["", ""]])[-1][1]
        wiki_annotated_for_entity = kind_of_sport + " " + occupation + " " + instance_of
        sport_flag = bool(re.search(KIND_OF_SPORTS_TEMPLATE, wiki_annotated_for_entity)) or bool(
            re.search(ATHLETE_TEMPLETE, wiki_annotated_for_entity)) or bool(
            re.search(SPORT_TEMPLATE, wiki_annotated_for_entity))
        if sport_flag:
            it_is_athlete = bool(re.search(r"human", instance_of)) or bool(re.search(ATHLETE_TEMPLETE, occupation))
            dict_entity = {"name": entity}
            if it_is_athlete:
                dict_entity["type"] = "athlete"

                dict_entity["country for sport"] = wiki_parser_for_entity.get("country for sport",
                                                                              [["", ""]])[-1][1]
                dict_entity["position played on team"] = wiki_parser_for_entity.get("position played on team",
                                                                                    [["", ""]])[-1][1]
                dict_entity["member of sport team"] = wiki_parser_for_entity.get("member of sport team",
                                                                                 [["", ""]])[0][1]
                dict_entity["id sport team"] = wiki_parser_for_entity.get("member of sport team",
                                                                          [["", ""]])[0][0]
            else:
                dict_entity["type"] = "team"

                dict_entity["victory"] = wiki_parser_for_entity.get("victory",
                                                                    [["", ""]])[-1][1]
                dict_entity["country"] = wiki_parser_for_entity.get("country",
                                                                    [["", ""]])[-1][1]
            array_sport_entities.append(dict_entity)
        else:
            pass
    if array_sport_entities:
        return array_sport_entities[-1]
    else:
        return {"type": "None"}


def get_dict_entity(entity_substr, entity_ids, type):
    try:
        WIKIDATA_URL = "http://wiki-parser:8077/model"
        dict_result = requests.post(WIKIDATA_URL,
                                    json={"parser_info": ["find_top_triplets"],
                                          "query": [[{"entity_substr": entity_substr,
                                                     "entity_ids": [entity_ids]}]]},
                                    timeout=1).json()
        if dict_result[0].get("topic_skill_entities_info", {}):
            big_dict_team = dict_result[0]["topic_skill_entities_info"].get(entity_substr, {})
        elif dict_result[0].get("entities_info", {}):
            big_dict_team = dict_result[0]["entities_info"].get(entity_substr, {})
        else:
            big_dict_team = {}
        small_dict_team = {"type": type,
                           "name": entity_substr,
                           "victory": big_dict_team.get("victory", [["", ""]])[-1][1],
                           "country": big_dict_team.get("country", [["", ""]])[-1][1]}
        return small_dict_team
    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        logger.exception(exc)
        return {"type": "None"}


##################################################################################################################
# LINK TO SPORT
##################################################################################################################


def link_to_like_sport_request(ngrams, vars):
    # SYS_LINK_TO_LIKE_SPORT
    link_to_opinion_about_sport = any(
        [req.lower() in state_utils.get_last_bot_utterance(vars)["text"].lower() for req in BINARY_QUESTION_ABOUT_SPORT]
    )
    user_agrees = condition_utils.is_yes_vars(vars)
    is_positive = "positive" in get_sentiment(
        state_utils.get_last_human_utterance(vars), probs=False, default_labels=["neutral"]
    )
    flag = link_to_opinion_about_sport and (user_agrees or is_positive)
    logger.info(f"link_to_like_sport_request={flag}")
    return flag


def link_to_like_athlete_request(ngrams, vars):
    # SYS_LINK_TO_LIKE_ATHLETE
    link_to_opinion_about_athl = any(
        [req.lower() in state_utils.get_last_bot_utterance(vars)["text"].lower() for req in
         BINARY_QUESTION_ABOUT_ATHLETE]
    )
    user_agrees = condition_utils.is_yes_vars(vars)
    is_positive = "positive" in get_sentiment(
        state_utils.get_last_human_utterance(vars), probs=False, default_labels=["neutral"]
    )
    flag = link_to_opinion_about_athl and (user_agrees or is_positive)
    logger.info(f"link_to_like_athlete_request={flag}")
    return flag


def link_to_like_comp_request(ngrams, vars):
    # SYS_LINK_TO_LIKE_COMP
    link_to_opinion_about_comp = any(
        [req.lower() in state_utils.get_last_bot_utterance(vars)["text"].lower() for req in BINARY_QUESTION_ABOUT_COMP]
    )
    user_agrees = condition_utils.is_yes_vars(vars)
    is_positive = "positive" in get_sentiment(
        state_utils.get_last_human_utterance(vars), probs=False, default_labels=["neutral"]
    )
    flag = link_to_opinion_about_comp and (user_agrees or is_positive)
    logger.info(f"link_to_like_comp_request={flag}")
    return flag


##################################################################################################################
# let's talk about sport || what kind of sport do you like
##################################################################################################################


def lets_talk_about_sport_request(ngrams, vars):
    # SYS_LETS_TALK_SPORT
    user_lets_chat_about_sport = if_chat_about_particular_topic(
        state_utils.get_last_human_utterance(vars),
        state_utils.get_last_bot_utterance(vars),
        compiled_pattern=SPORT_TEMPLATE)
    flag = bool(user_lets_chat_about_sport)
    logger.info(f"lets_talk_about_sport_request = {flag}")
    return flag


def user_ask_about_sport_request(ngrams, vars):
    # SYS_WHAT_SPORT
    user_ask = re.search(QUESTION_TEMPLATE, state_utils.get_last_human_utterance(vars)["text"])
    user_says_about_sports = re.search(SPORT_TEMPLATE, state_utils.get_last_human_utterance(vars)["text"])
    flag = bool(user_ask) and bool(user_says_about_sports)
    logger.info(f"user_ask_about_sport_request={flag}")
    return flag


def lets_chat_about_sport_response(vars):
    # USR_ASK_ABOUT_SPORT
    responses = [
        f"I have no physical embodiment. Sport is interesting and useful. Tell me what sport do you enjoy?",
        f"I live on a cloud, so i can't do sport , but I'm really curious about what sport are you fond of?",
    ]
    try:
        state_utils.set_confidence(vars, confidence=SUPER_CONFIDENCE)
        state_utils.set_can_continue(vars, continue_flag=MUST_CONTINUE)
        return random.choice(responses)
    except Exception as exc:
        logger.exception(exc)
        sentry_sdk.capture_exception(exc)
        state_utils.set_confidence(vars, ZERO_CONFIDENCE)
        return error_response(vars)


##################################################################################################################
# let's talk about athletes || who is you favourite athletes
##################################################################################################################


def lets_talk_about_athlete_request(ngrams, vars):
    # SYS_LETS_TALK_ATHLETE
    user_lets_chat_about_athlete = if_chat_about_particular_topic(
        state_utils.get_last_human_utterance(vars),
        state_utils.get_last_bot_utterance(vars),
        compiled_pattern=ATHLETE_TEMPLETE)

    flag = bool(user_lets_chat_about_athlete)
    logger.info(f"lets_talk_about_athlete_request={flag}")
    return flag


def user_ask_about_athletes_request(ngrams, vars):
    # SYS_WHO_FAVORITE_ATHLETE
    user_ask = re.search(QUESTION_TEMPLATE, state_utils.get_last_human_utterance(vars)["text"])
    user_says_about_athletes = re.search(ATHLETE_TEMPLETE, state_utils.get_last_human_utterance(vars)["text"])
    flag = bool(user_ask) and bool(user_says_about_athletes)
    logger.info(f"user_ask_about_athletes_request={flag}")
    return flag


def user_ask_about_athletes_response(vars):
    # USR_ASK_ABOUT_ATHLETE
    try:
        state_utils.set_confidence(vars, confidence=SUPER_CONFIDENCE)
        state_utils.set_can_continue(vars, continue_flag=MUST_CONTINUE)
        return f"I know all the athletes on this planet. Which athlete do you like the most?"
    except Exception as exc:
        logger.exception(exc)
        sentry_sdk.capture_exception(exc)
        state_utils.set_confidence(vars, ZERO_CONFIDENCE)
        return error_response(vars)


##################################################################################################################
# who do you support?
##################################################################################################################


def user_ask_who_do_u_support_request(ngrams, vars):
    # SYS_WHO_SUPPORT
    user_ask = re.search(QUESTION_TEMPLATE, state_utils.get_last_human_utterance(vars)["text"])
    user_says_about_support = re.search(SUPPORT_TEMPLATE, state_utils.get_last_human_utterance(vars)["text"])
    flag = bool(user_ask) and bool(user_says_about_support)
    logger.info(f"user_ask_who_do_u_support_request={flag}")
    return flag


def user_ask_who_do_u_support_response(vars):
    # USR_ASK_WHO_SUPPORT
    responses = ["sports teams", "athletes"]
    try:
        state_utils.set_confidence(vars, confidence=SUPER_CONFIDENCE)
        state_utils.set_can_continue(vars, continue_flag=MUST_CONTINUE)
        return f"I was born quite recently. But I know a lot of {random.choice(responses)}. Tell me who do you support?"
    except Exception as exc:
        logger.exception(exc)
        sentry_sdk.capture_exception(exc)
        state_utils.set_confidence(vars, ZERO_CONFIDENCE)
        return error_response(vars)


##################################################################################################################
# i like basketball || (after question human will say only kind of sport : football)
##################################################################################################################


def user_like_sport_request(ngrams, vars):
    # SYS_TELL_SPORT
    user_want = not_negative_emotion(vars)
    user_says_about_kind_of_sport = re.search(KIND_OF_SPORTS_TEMPLATE,
                                              state_utils.get_last_human_utterance(vars)["text"])
    if bool(user_says_about_kind_of_sport):
        flag_1 = bool(user_says_about_kind_of_sport) and user_want
        flag_2 = len(state_utils.get_last_human_utterance(vars)["text"]) == len(user_says_about_kind_of_sport.group())
        flag = flag_1 or flag_2
    else:
        flag = False
    logger.info(f"user_like_sport_request={flag}")
    return flag


def user_like_sport_response(vars):
    # USR_WHY_LIKE_SPORT
    try:
        number = random.randint(1, 10)
        kind_of_sport = re.search(KIND_OF_SPORTS_TEMPLATE,
                                  state_utils.get_last_human_utterance(vars)["text"]).group()
        state_utils.save_to_shared_memory(vars, kind_of_sport=kind_of_sport)
        state_utils.set_can_continue(vars, continue_flag=MUST_CONTINUE)
        if number > NUMBER_PROBABILITY:
            state_utils.set_confidence(vars, confidence=SUPER_CONFIDENCE)
            return f"why do you like {kind_of_sport}?"
        else:
            state_utils.set_confidence(vars, confidence=HIGH_CONFIDENCE)
            news = get_news(kind_of_sport)
            return news
    except Exception as exc:
        logger.exception(exc)
        sentry_sdk.capture_exception(exc)
        state_utils.set_confidence(vars, ZERO_CONFIDENCE)
        return error_response(vars)


##################################################################################################################
# if human have no_negative emotion after why like kind_of_sport -> i ask famous athlete
##################################################################################################################


def user_positive_or_neutral_about_kind_of_sport_request(ngrams, vars):
    # SYS_NOT_NEGATIVE_AFTER_Y_KIND_OF_SPORT
    flag = not_negative_emotion(vars)
    logger.info(f"user_positive_or_neutral_about_kind_of_sport_request={flag}")
    return flag


def user_positive_or_neutral_about_kind_of_sport_response(vars):
    # USR_HAVE_ATH_FROM_THIS_SPORT
    try:
        shared_memory = state_utils.get_shared_memory(vars)
        kind_of_sport = shared_memory.get("kind_of_sport", "")
        state_utils.set_can_continue(vars, continue_flag=CAN_CONTINUE_SCENARIO)
        state_utils.set_confidence(vars, confidence=HIGH_CONFIDENCE)
        return random.choice(ASK_ABOUT_ATH_IN_KIND_OF_SPORT).replace("KIND_OF_SPORT", kind_of_sport)
    except Exception as exc:
        logger.exception(exc)
        sentry_sdk.capture_exception(exc)
        state_utils.set_confidence(vars, ZERO_CONFIDENCE)
        return error_response(vars)


##################################################################################################################
# i like Ronaldo || some athlete who have team!
##################################################################################################################


def user_like_or_ask_about_player_request(ngrams, vars):
    # SYS_TELL_ATHLETE
    not_negative = not_negative_emotion(vars)
    dict_entity = entity_in_last_uttr_from_sport_area(vars)
    user_tell_athlete_with_team = dict_entity["type"] == "athlete" and len(
        dict_entity.get("member of sport team", "")) > 0
    flag = not_negative and user_tell_athlete_with_team
    logger.info(f"user_like_or_ask_about_player_request = {flag}")
    return flag


def user_like_or_ask_about_player_response(vars):
    # USR_LIKE_ATHLETE
    try:
        dict_athlete_with_team = entity_in_last_uttr_from_sport_area(vars)
        state_utils.save_to_shared_memory(vars, dict_athlete=dict_athlete_with_team)
        team = dict_athlete_with_team.get("member of sport team", "")
        position = dict_athlete_with_team.get("position played on team", "")
        if team:
            state_utils.set_can_continue(vars, continue_flag=MUST_CONTINUE)
            state_utils.set_confidence(vars, confidence=SUPER_CONFIDENCE)
            if position:
                response = random.choice(OPINION_ABOUT_ATHLETE_WITH_TEAM_AND_POS)
                response_replace = response.replace("TEAM", team).replace("POSITION", position)
            else:
                response = random.choice(OPINION_ABOUT_ATHLETE_WITH_TEAM)
                response_replace = response.replace("TEAM", team)
            return response_replace
        else:
            return last_chance_response(vars)
    except Exception as exc:
        logger.exception(exc)
        sentry_sdk.capture_exception(exc)
        state_utils.set_confidence(vars, confidence=ZERO_CONFIDENCE)
        return error_response(vars)


#####################################################################################################################
# some athlete who does not have team! or neg emotion
#####################################################################################################################


def user_like_or_ask_about_player_without_team_request(ngrams, vars):
    # SYS_TELL_ATHLETE_WITHOUT_TEAM
    not_negative = not_negative_emotion(vars)
    dict_entity = entity_in_last_uttr_from_sport_area(vars)
    user_tell_athlete_without_team = dict_entity["type"] == "athlete" and len(
        dict_entity.get("member of sport team", "")) == 0
    flag = not_negative and user_tell_athlete_without_team
    logger.info(f"user_like_or_ask_about_player_request = {flag}")
    return flag


def link_to_travel_response(vars):
    # USR_LINK_TO_TRAVEL
    try:
        state_utils.set_can_continue(vars, continue_flag=CAN_NOT_CONTINUE)
        state_utils.set_confidence(vars, confidence=SUPER_CONFIDENCE)
        shared_memory = state_utils.get_shared_memory(vars)
        dict_athlete = shared_memory.get("dict_athlete", {})
        dict_team = shared_memory.get("dict_team", {})
        information_flag = False
        if dict_athlete:
            country = dict_athlete.get("country for sport", "")
            name = dict_athlete.get("name", "")
            if country and name:
                information_flag = True
        if not information_flag and dict_team:
            country = dict_team.get("country", "")
            name = dict_team.get("name", "")
            if country and name:
                information_flag = True
        if information_flag:
            response = random.choice(OPINION_ABOUT_ATHLETE_WITHOUT_TEAM)
            response_replace = response.replace("COUNTRY", country).replace("NAME", name)
            return response_replace
        else:
            return last_chance_response(vars)
    except Exception as exc:
        logger.exception(exc)
        sentry_sdk.capture_exception(exc)
        state_utils.set_confidence(vars, confidence=ZERO_CONFIDENCE)
        return error_response(vars)


#####################################################################################################################
# user tell team or user not negative after comment athlete with team
#####################################################################################################################


def user_tell_team_request(ngrams, vars):
    # SYS_TELL_TEAM
    user_not_negative = not_negative_emotion(vars)
    dict_entity = entity_in_last_uttr_from_sport_area(vars)
    user_tell_team = dict_entity["type"] == "team"
    flag = user_not_negative and user_tell_team
    logger.info(f"user_tell_team_request = {flag}")
    return flag


def user_not_neg_after_comment_ath_with_team_request(ngrams, vars):
    # SYS_NOT_NEG_AFTER_ATHLETE_WITH_TEAM
    flag = not_negative_emotion(vars)
    logger.info(f"user_not_neg_after_comment_ath_with_team_request = {flag}")
    return flag


def user_get_talk_about_team_response(vars):
    # USR_GET_OPIN_ABOUT_TEAM
    try:
        dict_entity = entity_in_last_uttr_from_sport_area(vars)
        if dict_entity["type"] == "team":
            state_utils.save_to_shared_memory(vars, dict_team=dict_entity)
            competition = dict_entity["victory"]
            country = dict_entity["country"]
            name_team = dict_entity["name"]
        else :
            shared_memory = state_utils.get_shared_memory(vars)
            dict_athlete = shared_memory.get("dict_athlete", {})
            name_team = dict_athlete["member of sport team"]
            id_team = dict_athlete["id sport team"]
            dict_team = get_dict_entity(name_team, id_team, "team")
            state_utils.save_to_shared_memory(vars, dict_team=dict_team)
            competition = dict_team.get("victory", "")
            country = dict_team.get("country", "")
        if competition:
            state_utils.set_can_continue(vars, continue_flag=CAN_CONTINUE_SCENARIO)
            state_utils.set_confidence(vars, confidence=HIGH_CONFIDENCE)
            response = random.choice(OPINION_ABOUT_TEAM)
            response_replace = response.replace("TEAM", name_team).replace("COMPETITION", competition)
            return response_replace
        elif country:
            state_utils.set_can_continue(vars, continue_flag=CAN_NOT_CONTINUE)
            state_utils.set_confidence(vars, confidence=HIGH_CONFIDENCE)
            return f"Oh, that's a cool team. I know they are from {country}. Have you ever been there?"
        else:
            return last_chance_response(vars)
    except Exception as exc:
        logger.exception(exc)
        sentry_sdk.capture_exception(exc)
        state_utils.set_confidence(vars, confidence=ZERO_CONFIDENCE)
        return error_response(vars)


##################################################################################################################
# do you like competition? || let's talk about tournament
##################################################################################################################


def user_lets_talk_about_comp_request(ngrams, vars):
    # SYS_LETS_TALK_ABOUT_COMP
    user_lets_chat_about_comp = if_chat_about_particular_topic(
        state_utils.get_last_human_utterance(vars),
        state_utils.get_last_bot_utterance(vars),
        compiled_pattern=COMPETITION_TEMPLATE)
    flag = bool(user_lets_chat_about_comp)
    logger.info(f"user_lets_talk_about_comp_request={flag}")
    return flag


def user_not_neg_after_comment_team_request(ngrams, vars):
    # SYS_NOT_NEG_AFT_COMMENT_TEAM
    flag = not_negative_emotion(vars)
    logger.info(f"user_not_neg_after_comment_team_request = {flag}")
    return flag


def user_ask_about_comp_request(ngrams, vars):
    # SYS_ASK_ABOUT_COMP
    user_ask = re.search(QUESTION_TEMPLATE, state_utils.get_last_human_utterance(vars)["text"])
    user_said_about_comp = re.search(COMPETITION_TEMPLATE, state_utils.get_last_human_utterance(vars)["text"])
    flag = bool(user_ask) and bool(user_said_about_comp)
    logger.info(f"user_ask_about_comp_request={flag}")
    return flag


def user_ask_about_comp_response(vars):
    # USR_ASK_ABOUT_COMP
    try:
        shared_memory = state_utils.get_shared_memory(vars)
        dict_team = shared_memory.get("dict_team", {})
        if dict_team:
            competition = dict_team.get("victory", "")
        else:
            response_competition = ["UFC", "FIFA World Cup", "Super Bowl", "NBA", "Rugby World Cup", "Stanley Cup"]
            competition = random.choice(response_competition)
        state_utils.set_confidence(vars, confidence=SUPER_CONFIDENCE)
        state_utils.set_can_continue(vars, continue_flag=MUST_CONTINUE)
        return (
            f"Well. if I had a physical embodiment, I would like to go to the {competition} "
            f"and see this wonderful tournament.Do you have a favorite competition?"
        )
    except Exception as exc:
        logger.exception(exc)
        sentry_sdk.capture_exception(exc)
        state_utils.set_confidence(vars, ZERO_CONFIDENCE)
        return error_response(vars)


##################################################################################################################
# i like Super Bowl   # в другом пр проверять регэксп
##################################################################################################################


def user_like_comp_request(ngrams, vars):
    # SYS_TELL_COMP
    not_negative = not_negative_emotion(vars)
    user_says_about_kind_of_comp = re.search(KIND_OF_COMPETITION_TEMPLATE,
                                             state_utils.get_last_human_utterance(vars)["text"])
    flag = not_negative and bool(user_says_about_kind_of_comp)
    logger.info(f"user_like_comp_request={flag}")
    return flag


def user_like_comp_response(vars):
    # USR_WHY_LIKE_COMP
    try:
        number = random.randint(1, 10)
        kind_of_comp = re.search(
            KIND_OF_COMPETITION_TEMPLATE, state_utils.get_last_human_utterance(vars)["text"]
        ).group()
        state_utils.save_to_shared_memory(vars, kind_of_comp=kind_of_comp)
        state_utils.set_confidence(vars, confidence=SUPER_CONFIDENCE)
        state_utils.set_can_continue(vars, continue_flag=MUST_CONTINUE)
        if number > NUMBER_PROBABILITY:
            return f"why do you like {kind_of_comp}?"
        else:
            news = get_news(kind_of_comp)
            return news
    except Exception as exc:
        logger.exception(exc)
        sentry_sdk.capture_exception(exc)
        state_utils.set_confidence(vars, ZERO_CONFIDENCE)
        return error_response(vars)


##################################################################################################################
# user not negative and we propose to discuss the fact about COMP
##################################################################################################################


def user_positive_or_neutral_about_comp_request(ngrams, vars):
    # SYS_NOT_NEGATIVE_AFTER_Y_COMP
    flag = not_negative_emotion(vars)
    logger.info(f"user_positive_or_neutral_about_comp_request={flag}")
    return flag


def user_positive_or_neutral_about_comp_response(vars):
    # USR_OFFER_FACT_ABOUT_COMP
    try:
        shared_memory = state_utils.get_shared_memory(vars)
        competition = shared_memory.get("kind_of_comp", "")
        if competition:
            fact_about_discussed_competition = send_cobotqa(f"fact about {competition}")
        else:
            fact_about_discussed_competition = ""
        if fact_about_discussed_competition and competition:
            state_utils.save_to_shared_memory(
                vars,
                fact_about_discussed_competition=fact_about_discussed_competition
            )
            state_utils.set_confidence(vars, confidence=HIGH_CONFIDENCE)
            state_utils.set_can_continue(vars, continue_flag=CAN_CONTINUE_SCENARIO)
            offer_fact = random.choice(OFFER_FACT_COMPETITION).replace("COMPETITION", competition)
            return offer_fact
        else:
            return last_chance_response(vars)
    except Exception as exc:
        logger.exception(exc)
        sentry_sdk.capture_exception(exc)
        state_utils.set_confidence(vars, ZERO_CONFIDENCE)
        return error_response(vars)


##################################################################################################################
# user want fact about COMP
##################################################################################################################


def user_want_fact_about_comp_request(ngrams, vars):
    # SYS_WANT_FACT_ABOUT_COMP
    flag = not_negative_emotion(vars)
    logger.info(f"user_want_fact_about_comp_request={flag}")
    return flag


def user_want_fact_about_comp_response(vars):
    # USR_GET_FACT_ABOUT_COMP
    try:
        shared_memory = state_utils.get_shared_memory(vars)
        fact_about_discussed_competition = shared_memory.get("fact_about_discussed_competition", "")
        if fact_about_discussed_competition:
            opinion_req = random.choice(OPINION_REQUESTS)
            state_utils.set_confidence(vars, HIGH_CONFIDENCE)
            state_utils.set_can_continue(vars, continue_flag=CAN_CONTINUE_SCENARIO_DONE)
            return f"{fact_about_discussed_competition} {opinion_req}"
        else:
            return last_chance_response(vars)
    except Exception as exc:
        logger.exception(exc)
        sentry_sdk.capture_exception(exc)
        state_utils.set_confidence(vars, ZERO_CONFIDENCE)
        return error_response(vars)


##################################################################################################################
# negative -> exit from the skill
##################################################################################################################


def user_negative_request(ngrams, vars):
    # SYS_TELL_NEGATIVE
    is_negative = "negative" in get_sentiment(state_utils.get_last_human_utterance(vars),
                                              probs=False, default_labels=["neutral"])
    no_vars = condition_utils.is_no_vars(vars)
    flag = is_negative or no_vars
    logger.info(f"user_negative_request={flag}")
    return flag


def user_negative_response(ngrams, vars):
    # USR_TELL_NEGATIVE
    try:
        state_utils.set_confidence(vars, SUPER_CONFIDENCE)
        state_utils.set_can_continue(vars, continue_flag=MUST_CONTINUE)
        prev_active_skills = [uttr.get("active_skill", "")
                              for uttr in vars["agent"]["dialog"]["bot_utterances"]][-5:]
        if "dff_travel_skill" in prev_active_skills:
            body = compose_topic_offering(excluded_skills=prev_active_skills)
            return body
        else:
            countries = ["Russia", "China", "Germany"]
            return f"I know that sports are very popular in {random.choice(countries)}. Have you ever been there?"
    except Exception as exc:
        logger.exception(exc)
        sentry_sdk.capture_exception(exc)
        state_utils.set_confidence(vars, ZERO_CONFIDENCE)
        return error_response(vars)


##################################################################################################################
# last chance == fullback
##################################################################################################################


def last_chance_request(ngrams, vars):
    # SYS_LAST_CHANCE
    flag = True
    logger.info(f"last_chance_request = {flag}")
    return flag


def last_chance_response(vars):
    # USR_LAST_CHANCE
    try:
        state_utils.set_confidence(vars, HIGH_CONFIDENCE)
        state_utils.set_can_continue(vars, continue_flag=CAN_CONTINUE_SCENARIO)
        return random.choice(LAST_CHANCE_TEMPLATE)
    except Exception as exc:
        logger.exception(exc)
        sentry_sdk.capture_exception(exc)
        state_utils.set_confidence(vars, ZERO_CONFIDENCE)
        return error_response(vars)


##################################################################################################################
# error
##################################################################################################################


def error_response(vars):
    state_utils.set_confidence(vars, ZERO_CONFIDENCE)
    return f""


##################################################################################################################
# START

simplified_dialogflow.add_user_serial_transitions(
    State.USR_START,
    {
        State.SYS_WHAT_SPORT: user_ask_about_sport_request,
        State.SYS_WHO_FAVORITE_ATHLETE: user_ask_about_athletes_request,
        State.SYS_WHO_SUPPORT: user_ask_who_do_u_support_request,
        State.SYS_ASK_ABOUT_COMP: user_ask_about_comp_request,
        State.SYS_TELL_SPORT: user_like_sport_request,
        State.SYS_TELL_ATHLETE: user_like_or_ask_about_player_request,
        State.SYS_TELL_ATHLETE_WITHOUT_TEAM: user_like_or_ask_about_player_without_team_request,
        State.SYS_TELL_TEAM: user_tell_team_request,
        State.SYS_TELL_COMP: user_like_comp_request,
        State.SYS_LETS_TALK_ABOUT_COMP: user_lets_talk_about_comp_request,
        State.SYS_LETS_TALK_ATHLETE: lets_talk_about_athlete_request,
        State.SYS_LETS_TALK_SPORT: lets_talk_about_sport_request,
        State.SYS_LINK_TO_LIKE_SPORT: link_to_like_sport_request,
        State.SYS_LINK_TO_LIKE_COMP: link_to_like_comp_request,
        State.SYS_LINK_TO_LIKE_ATHLETE: link_to_like_athlete_request
    },
)
simplified_dialogflow.set_error_successor(State.USR_START, State.SYS_ERR)

##################################################################################################################
# SYS_WHO_FAVORITE_ATHLETE || SYS_LETS_TALK_ATHLETE || SYS_LINK_TO_LIKE_ATHLETE--> USR_ASK_ABOUT_ATHLETE

simplified_dialogflow.add_system_transition(
    State.SYS_WHO_FAVORITE_ATHLETE, State.USR_ASK_ABOUT_ATHLETE, user_ask_about_athletes_response
)

simplified_dialogflow.add_system_transition(
    State.SYS_LETS_TALK_ATHLETE, State.USR_ASK_ABOUT_ATHLETE, user_ask_about_athletes_response
)
simplified_dialogflow.add_system_transition(
    State.SYS_LINK_TO_LIKE_ATHLETE, State.USR_ASK_ABOUT_ATHLETE, user_ask_about_athletes_response
)
simplified_dialogflow.add_user_serial_transitions(
    State.USR_ASK_ABOUT_ATHLETE,
    {
        State.SYS_TELL_ATHLETE: user_like_or_ask_about_player_request,
        State.SYS_TELL_SPORT: user_like_sport_request,
        State.SYS_TELL_NEGATIVE: user_negative_request,
        State.SYS_LAST_CHANCE: last_chance_request
    },
)
simplified_dialogflow.set_error_successor(State.USR_ASK_ABOUT_ATHLETE, State.SYS_ERR)

##################################################################################################################
# SYS_NOT_NEG_AFT_COMMENT_TEAM || SYS_ASK_ABOUT_COMP || SYS_LETS_TALK_ABOUT_COMP || SYS_LINK_TO_LIKE_COMP
# --> USR_ASK_ABOUT_COMP

simplified_dialogflow.add_system_transition(
    State.SYS_ASK_ABOUT_COMP, State.USR_ASK_ABOUT_COMP, user_ask_about_comp_response
)

simplified_dialogflow.add_system_transition(
    State.SYS_LETS_TALK_ABOUT_COMP, State.USR_ASK_ABOUT_COMP, user_ask_about_comp_response
)

simplified_dialogflow.add_system_transition(
    State.SYS_LINK_TO_LIKE_COMP, State.USR_ASK_ABOUT_COMP, user_ask_about_comp_response
)

simplified_dialogflow.add_system_transition(
    State.SYS_NOT_NEG_AFT_COMMENT_TEAM, State.USR_ASK_ABOUT_COMP, user_ask_about_comp_response
)

simplified_dialogflow.add_user_serial_transitions(
    State.USR_ASK_ABOUT_COMP,
    {
        State.SYS_TELL_COMP: user_like_comp_request,
        State.SYS_TELL_NEGATIVE: user_negative_request,
        State.SYS_LAST_CHANCE: last_chance_request
    },
)
simplified_dialogflow.set_error_successor(State.USR_ASK_ABOUT_COMP, State.SYS_ERR)

##################################################################################################################
# SYS_TELL_COMP --> USR_WHY_LIKE_COMP

simplified_dialogflow.add_system_transition(State.SYS_TELL_COMP, State.USR_WHY_LIKE_COMP, user_like_comp_response)

simplified_dialogflow.add_user_serial_transitions(
    State.USR_WHY_LIKE_COMP,
    {
        State.SYS_NOT_NEGATIVE_AFTER_Y_COMP: user_positive_or_neutral_about_comp_request,
        State.SYS_TELL_NEGATIVE: user_negative_request,
        State.SYS_LAST_CHANCE: last_chance_request
    },
)
simplified_dialogflow.set_error_successor(State.USR_WHY_LIKE_COMP, State.SYS_ERR)

##################################################################################################################
# SYS_WHO_SUPPORT --> USR_ASK_WHO_SUPPORT

simplified_dialogflow.add_system_transition(
    State.SYS_WHO_SUPPORT, State.USR_ASK_WHO_SUPPORT, user_ask_who_do_u_support_response
)

simplified_dialogflow.add_user_serial_transitions(
    State.USR_ASK_WHO_SUPPORT,
    {
        State.SYS_TELL_ATHLETE: user_like_or_ask_about_player_request,
        State.SYS_TELL_SPORT: user_like_sport_request,
        State.SYS_TELL_NEGATIVE: user_negative_request,
        State.SYS_LAST_CHANCE: last_chance_request
    },
)
simplified_dialogflow.set_error_successor(State.USR_ASK_WHO_SUPPORT, State.SYS_ERR)

##################################################################################################################
# SYS_LETS_TALK_SPORT || SYS_WHAT_SPORT || SYS_LINK_TO_LIKE_SPORT --> USR_ASK_ABOUT_SPORT

simplified_dialogflow.add_system_transition(
    State.SYS_LETS_TALK_SPORT, State.USR_ASK_ABOUT_SPORT, lets_chat_about_sport_response
)
simplified_dialogflow.add_system_transition(
    State.SYS_WHAT_SPORT, State.USR_ASK_ABOUT_SPORT, lets_chat_about_sport_response
)
simplified_dialogflow.add_system_transition(
    State.SYS_LINK_TO_LIKE_SPORT, State.USR_ASK_ABOUT_SPORT, lets_chat_about_sport_response
)

simplified_dialogflow.add_user_serial_transitions(
    State.USR_ASK_ABOUT_SPORT,
    {
        State.SYS_TELL_SPORT: user_like_sport_request,
        State.SYS_TELL_ATHLETE: user_like_or_ask_about_player_request,
        State.SYS_TELL_NEGATIVE: user_negative_request,
        State.SYS_LAST_CHANCE: last_chance_request
    },
)
simplified_dialogflow.set_error_successor(State.USR_ASK_ABOUT_SPORT, State.SYS_ERR)

##################################################################################################################
# SYS_TELL_SPORT --> USR_WHY_LIKE_SPORT

simplified_dialogflow.add_system_transition(State.SYS_TELL_SPORT, State.USR_WHY_LIKE_SPORT, user_like_sport_response)

simplified_dialogflow.add_user_serial_transitions(
    State.USR_WHY_LIKE_SPORT,
    {
        State.SYS_TELL_ATHLETE: user_like_or_ask_about_player_request,
        State.SYS_TELL_TEAM: user_tell_team_request,
        State.SYS_TELL_ATHLETE_WITHOUT_TEAM: user_like_or_ask_about_player_without_team_request,
        State.SYS_NOT_NEGATIVE_AFTER_Y_KIND_OF_SPORT: user_positive_or_neutral_about_kind_of_sport_request,
        State.SYS_TELL_NEGATIVE: user_negative_request,
        State.SYS_LAST_CHANCE: last_chance_request
    },
)
simplified_dialogflow.set_error_successor(State.USR_WHY_LIKE_SPORT, State.SYS_ERR)

##################################################################################################################
# SYS_NOT_NEGATIVE_AFTER_Y_KIND_OF_SPORT --> USR_HAVE_ATH_FROM_THIS_SPORT

simplified_dialogflow.add_system_transition(State.SYS_NOT_NEGATIVE_AFTER_Y_KIND_OF_SPORT,
                                            State.USR_HAVE_ATH_FROM_THIS_SPORT,
                                            user_positive_or_neutral_about_kind_of_sport_response)
simplified_dialogflow.add_user_serial_transitions(
    State.USR_HAVE_ATH_FROM_THIS_SPORT,
    {
        State.SYS_TELL_ATHLETE: user_like_or_ask_about_player_request,
        State.SYS_TELL_TEAM: user_tell_team_request,
        State.SYS_TELL_ATHLETE_WITHOUT_TEAM: user_like_or_ask_about_player_without_team_request,
        State.SYS_TELL_NEGATIVE: user_negative_request,
        State.SYS_LAST_CHANCE: last_chance_request
    },
)
simplified_dialogflow.set_error_successor(State.USR_WHY_LIKE_SPORT, State.SYS_ERR)

##################################################################################################################
# SYS_TELL_ATHLETE --> USR_LIKE_ATHLETE

simplified_dialogflow.add_system_transition(
    State.SYS_TELL_ATHLETE, State.USR_LIKE_ATHLETE, user_like_or_ask_about_player_response
)
simplified_dialogflow.add_user_serial_transitions(
    State.USR_LIKE_ATHLETE,
    {
        State.SYS_NOT_NEG_AFTER_ATHLETE_WITH_TEAM: user_not_neg_after_comment_ath_with_team_request,
        State.SYS_TELL_NEGATIVE: user_negative_request,
        State.SYS_LAST_CHANCE: last_chance_request
    },
)
simplified_dialogflow.set_error_successor(State.USR_LIKE_ATHLETE, State.SYS_ERR)

##################################################################################################################
# SYS_TELL_ATHLETE_WITHOUT_TEAM || --> USR_LINK_TO_TRAVEL

simplified_dialogflow.add_system_transition(
    State.SYS_TELL_ATHLETE_WITHOUT_TEAM, State.USR_LINK_TO_TRAVEL, link_to_travel_response
)

##################################################################################################################
# SYS_NOT_NEG_AFTER_ATHLETE_WITH_TEAM || SYS_TELL_TEAM --> USR_GET_OPIN_ABOUT_TEAM

simplified_dialogflow.add_system_transition(
    State.SYS_TELL_TEAM, State.USR_GET_OPIN_ABOUT_TEAM, user_get_talk_about_team_response
)

simplified_dialogflow.add_system_transition(
    State.SYS_NOT_NEG_AFTER_ATHLETE_WITH_TEAM, State.USR_GET_OPIN_ABOUT_TEAM, user_get_talk_about_team_response
)

simplified_dialogflow.add_user_serial_transitions(
    State.USR_GET_OPIN_ABOUT_TEAM,
    {
        State.SYS_NOT_NEG_AFT_COMMENT_TEAM: user_not_neg_after_comment_team_request,
        State.SYS_TELL_NEGATIVE: user_negative_request,
        State.SYS_LAST_CHANCE: last_chance_request
    },
)

simplified_dialogflow.set_error_successor(State.USR_GET_OPIN_ABOUT_TEAM, State.SYS_ERR)

##################################################################################################################
# SYS_NOT_NEGATIVE_AFTER_Y_COMP --> USR_OFFER_FACT_ABOUT_COMP

simplified_dialogflow.add_system_transition(
    State.SYS_NOT_NEGATIVE_AFTER_Y_COMP,
    State.USR_OFFER_FACT_ABOUT_COMP,
    user_positive_or_neutral_about_comp_response
)

simplified_dialogflow.add_user_serial_transitions(
    State.USR_OFFER_FACT_ABOUT_COMP,
    {
        State.SYS_WANT_FACT_ABOUT_COMP: user_want_fact_about_comp_request,
        State.SYS_TELL_NEGATIVE: user_negative_request,
        State.SYS_LAST_CHANCE: last_chance_request
    },
)

simplified_dialogflow.set_error_successor(State.USR_OFFER_FACT_ABOUT_COMP, State.SYS_ERR)

##################################################################################################################
# SYS_WANT_FACT_ABOUT_COMP -> USR_GET_FACT_ABOUT_COMP

simplified_dialogflow.add_system_transition(
    State.SYS_WANT_FACT_ABOUT_COMP, State.USR_GET_FACT_ABOUT_COMP, user_want_fact_about_comp_response
)

simplified_dialogflow.add_user_serial_transitions(
    State.USR_GET_FACT_ABOUT_COMP,
    {
        State.SYS_TELL_NEGATIVE: user_negative_request,
        State.SYS_LAST_CHANCE: last_chance_request
    },
)

simplified_dialogflow.set_error_successor(State.USR_GET_FACT_ABOUT_COMP, State.SYS_ERR)
##################################################################################################################
# SYS_LAST_CHANCE -> USR_LAST_CHANCE

simplified_dialogflow.add_system_transition(
    State.SYS_LAST_CHANCE, State.USR_LAST_CHANCE, last_chance_response
)

simplified_dialogflow.add_user_serial_transitions(
    State.USR_LAST_CHANCE,
    {
        State.SYS_WHAT_SPORT: user_ask_about_sport_request,
        State.SYS_WHO_FAVORITE_ATHLETE: user_ask_about_athletes_request,
        State.SYS_WHO_SUPPORT: user_ask_who_do_u_support_request,
        State.SYS_ASK_ABOUT_COMP: user_ask_about_comp_request,
        State.SYS_TELL_SPORT: user_like_sport_request,
        State.SYS_TELL_ATHLETE: user_like_or_ask_about_player_request,
        State.SYS_TELL_ATHLETE_WITHOUT_TEAM: user_like_or_ask_about_player_without_team_request,
        State.SYS_TELL_TEAM: user_tell_team_request,
        State.SYS_TELL_COMP: user_like_comp_request,
        State.SYS_LETS_TALK_ABOUT_COMP: user_lets_talk_about_comp_request,
        State.SYS_LETS_TALK_ATHLETE: lets_talk_about_athlete_request,
        State.SYS_LETS_TALK_SPORT: lets_talk_about_sport_request,
        State.SYS_TELL_NEGATIVE: user_negative_request
    },
)

##################################################################################################################
# SYS_TELL_NEGATIVE -> USR_TELL_NEGATIVE

simplified_dialogflow.add_system_transition(
    State.SYS_TELL_NEGATIVE, State.USR_TELL_NEGATIVE, user_negative_response
)

##################################################################################################################
# SYS_ERR

simplified_dialogflow.add_system_transition(
    State.SYS_ERR,
    (scopes.MAIN, scopes.State.USR_ROOT),
    error_response,
)

dialogflow = simplified_dialogflow.get_dialogflow()
