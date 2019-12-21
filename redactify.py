#!/usr/bin/env python

# find plug in command arguments at https://gitlab.gnome.org/GNOME/gimp/blob/master/app/pdb/plug-in-compat-cmds.c
from gimpfu import *
import json
import re
import math
import random
import base64
import tempfile

def write_text(img, font, text, y, size, justification="left", position='center', border=False):
    width = img.width
    height = img.height
    w, h, a, d = pdb.gimp_text_get_extents_fontname(text, size, PIXELS, font)

    w += 2 * width / 76.8

    if position == 'center':
        x = (width - w) / 2
    else:
        x = width / 12.4

    if position == 'bottom':
        y -= h

    text_layer = pdb.gimp_text_fontname(img, None, x, y, text, width / 76.8, True, size, PIXELS, font)

    if justification == 'center':
        pdb.gimp_text_layer_set_justification(text_layer, TEXT_JUSTIFY_CENTER)

    if border:
        x1 = width / 200
        x2 = w - x1
        y1 = x1
        y2 = h - x1 + d + 2 * width / 76.8

        layer = gimp.Layer(img, "border", text_layer.width, text_layer.height, RGB_IMAGE, 100, LAYER_MODE_NORMAL)
        img.add_layer(layer, 0)
        pdb.gimp_layer_add_alpha(layer)
        pdb.gimp_edit_clear(layer)
        pdb.gimp_layer_translate(layer, x, y)

        pdb.gimp_context_push()
        pdb.gimp_context_set_brush(pdb.gimp_brushes_list("Hardness")[1][-1])
        pdb.gimp_context_set_brush_size(width / 200)
        pdb.gimp_paintbrush_default(layer, 10, [x1, y1, x1, y2, x2, y2, x2, y1, x1, y1])
        pdb.gimp_context_pop()

    return h

def convert_layer_to_paper(img, drawable):
    pdb.gimp_edit_fill(drawable, BACKGROUND_FILL)
    pdb.plug_in_rgb_noise(img, drawable, 0, 0, 0.20, 1, 0, 0)

def add_text(img, drawable, font, title, details, body, footer):
    width = img.width
    height = img.height

    H = width / 19.2

    H += width / 38.4 + write_text(img, font, title, H, width / 12.4, "center", position="center", border=True)
    H += width / 25.6 + write_text(img, font, details, H, width / (12.4 * 4))
    H += width / 25.6 + write_text(img, font, body, H, width / (12.4 * 4))

    if footer:
        dh = write_text(img, font, footer, height - width / 9.6, width / (12.4 * 4), position='bottom', border=True)

def redact(img, drawable, regexes):
    regexs = re.split('(?<!\\\\)&', regexes)
    for regex in regexs:
        regex = regex.replace('\\&', '&')
        for layer in img.layers:
            if pdb.gimp_item_is_text_layer(layer):
                body = pdb.gimp_text_layer_get_text(layer)
                try:
                    for match in re.findall(regex, body):
                        replacement = u'\u2588' * len(match)
                        body = re.sub(match, replacement, body)
                    pdb.gimp_text_layer_set_text(layer, body)
                except:
                    pdb.gimp_message('couldn\'t use regex')


def finalize(img, drawable, angle, do_photocopy=False):
    width = img.width
    height = img.height

    flat_layer = pdb.gimp_image_flatten(img)
    pdb.gimp_layer_add_alpha(flat_layer)

    pdb.gimp_rotate(flat_layer, False, angle)
    pdb.gimp_context_set_foreground((0, 0, 0))
    pdb.plug_in_rgb_noise(img, flat_layer, 0, 0, 0.20, 1, 0, 0)

    layer = gimp.Layer(img, "redactify_overlay", width, height, RGB_IMAGE, 4.5, LAYER_MODE_HARD_MIX)
    img.add_layer(layer, 0)
    pdb.gimp_layer_add_alpha(layer)
    pdb.gimp_edit_fill(layer, BACKGROUND_FILL)
    pdb.plug_in_rgb_noise(img, layer, 0, 0, 1, 0, 0, 0)

    if do_photocopy:
        flat_layer = pdb.gimp_image_flatten(img)
        pdb.plug_in_photocopy(img, flat_layer, width / 24, 0.8, 0.17, 0.14)



register("python_fu_redactify_convert_layer_to_paper",
         "Makes the current layer have a papery apppearance",
         "Makes the current layer have a papery apppearance",
         "Cian Booth",
         "Cian Booth",
         "2019-2020",
         "<Image>/Filters/Redactify/1. Layer to Paper",
         "RGB*",
         [],
         [],
         convert_layer_to_paper)

register("python_fu_redactify_add_text",
         "Adds text to produce a pre-redacted document",
         "Adds text to produce a pre-redacted document",
         "Cian Booth",
         "Cian Booth",
         "2019-2020",
         "<Image>/Filters/Redactify/2. Add Text...",
         "RGB*",
         [
             (PF_FONT, "font", "Font", "Special Elite"),
             (PF_STRING, "title", "Title", "SECTOR 8 BRIEFING"),
             (PF_STRING, "details", "Details", "  MISSION: Alpha248-Wainscot\nPRIORITY: Disco/Foxtrot\n SECRECY: Mother Goose\nBRIEFING: Mz. F Young\n        DATE: 28/04/1923 (30c2)"),
             (PF_STRING, "body", "Body", "At 08:30 hours, a localised phenomena was detected at location GREENS PARK \nELEMENTARY SCHOOL . Mx L. Neptune was called in to confirm. Managed to send\none (1) photograph before loss of contact.\n\nAPPEARANCE:\n  * UNCLEAR - suspected to be wooden chairs\n\nKNOWN EFFECTS:\n  * MULTIPLICATION via MITOSIS\n  * VISUAL IMPAIRMENT within 20m\n  * LOSS OF LIFE - method unknown \n\nRESPONSE REQUIRED:\n  * ANALYZE VIABILITY FOR WEAPONIZATION\n  * REMOVE WITNESS TESTIMONY\n  * NEUTRALIZE PHENOMENA\n\nATTACHMENTS:\n    Degraded photograph of phenomena, note that subject has since\n    multiplied further after photograph was taken.\n\nATTENDEES:\n    Mz. F Young (BRIEFER)\n    Mr. T Crown (MINUTES)\n    FIRST PLAYER\n    SECOND PLAYER\n    THIRD PLAYER"),
             (PF_STRING, "footer", "Footer", "NOTE: \nAttendees were applied short-term antimnemonics\ndue to procedures related to event Oscar868-tremulous\nthat occurred shortly afterwards."),
         ],
         [],
         add_text)

register("python_fu_redactify_redact",
         "a '&' separated list of python regex to be replaced with solid blocks",
         "a '&' separated list of python regex to be replaced with solid blocks",
         "Cian Booth",
         "Cian Booth",
         "2019-2020",
         "<Image>/Filters/Redactify/3. Redact...",
         "RGB*",
         [
             (PF_STRING, "regexes", "Regex", "\\S+ PLAYER&Foxtrot&23&loss of contact&wooden chairs&MULTIPLICATION&MITOSIS&VISUAL&20&LOSS OF LIFE&ANALYZE VIABILITY FOR WEAPONIZATION&WITNESS TESTIMONY&subject has .*&multiplied further"),
         ],
         [],
         redact)

register("python_fu_redactify_finalize",
         "Adds polishing touches to a redacted document",
         "Adds polishing touches to a redacted document",
         "Cian Booth",
         "Cian Booth",
         "2019-2020",
         "<Image>/Filters/Redactify/4. Finalize...",
         "RGB*",
         [
             (PF_SLIDER, "angle", "Rotate Angle", 0, [-math.pi/180, math.pi/180, 1e-5]),
             (PF_TOGGLE, "do_photocopy", "Use Photocopy Style", False),
         ],
         [],
         finalize)


main()
