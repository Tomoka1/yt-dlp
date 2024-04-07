import functools

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    determine_ext,
    int_or_none,
    qualities,
    unified_timestamp,
    update_url_query,
    url_or_none,
    urlencode_postdata,
)

from ..utils.traversal import traverse_obj


class AfreecaTVIE(InfoExtractor):
    IE_NAME = 'afreecatv'
    IE_DESC = 'afreecatv.com'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:(?:live|afbbs|www)\.)?afreeca(?:tv)?\.com(?::\d+)?
                            (?:
                                /app/(?:index|read_ucc_bbs)\.cgi|
                                /player/[Pp]layer\.(?:swf|html)
                            )\?.*?\bnTitleNo=|
                            vod\.afreecatv\.com/(PLAYER/STATION|player)/
                        )
                        (?P<id>\d+)
                    '''
    _NETRC_MACHINE = 'afreecatv'
    _TESTS = [{
        # regular content
        'url': 'https://vod.afreecatv.com/player/121155561',
        'info_dict': {
            'id': '20240406_334AB13F_261384508_1',
            'title': '🍒 [04.06] 조커 어몽어스 (part 1)',
            'thumbnail': 're:^https?://(?:video|st)img.afreecatv.com/.*$',
            'ext': 'mp4',
            'uploader': '9호',
            'uploader_id': 'orexxs',
            'upload_date': '20240406',
            'duration': 17999,
            'timestamp': 1712406343,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # regular content
        'url': 'https://vod.afreecatv.com/player/121155561',
        'info_dict': {
            'id': '20240325_ACBC028E_259970062_1',
            'title': '감스트X지피티 정신개조 트레이닝',
            'thumbnail': 're:^https?://(?:video|st)img.afreecatv.com/.*$',
            'ext': 'mp4',
            'uploader': 'BJ지피티',
            'uploader_id': 'tjrdbs999',
            'upload_date': '20240325',
            'duration': 13629,
            'timestamp': 1711389319,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # adult content
        'url': 'https://vod.afreecatv.com/player/119630771',
        'info_dict': {
            'id': '20240320_4896C4D6_259321606_1',
            'title': 'ㅗㅜ..웽자기 오늘 12528 사랑해 승또구!!!처음이다!!만두개!! 감사합니다',
            'thumbnail': 're:^https?://(?:video|st)img.afreecatv.com/.*$',
            'ext': 'mp4',
            'uploader': '하루S2',
            'uploader_id': 'sol3712',
            'upload_date': '20240320',
            'duration': 1429,
            'timestamp': 1710970558,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # adult content
        'url': 'https://vod.afreecatv.com/player/121024417',
        'info_dict': {
            'id': '20240405_9E94EBAF_261220608_5',
            'title': '강남에서..무슨일이? (part 1)',
            'thumbnail': 're:^https?://(?:video|st)img.afreecatv.com/.*$',
            'ext': 'mp4',
            'uploader': '대세는BJ세야',
            'uploader_id': 'barams01',
            'upload_date': '20230108',
            'duration': 583,
            'timestamp': 1712280873,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _perform_login(self, username, password):
        login_form = {
            'szWork': 'login',
            'szType': 'json',
            'szUid': username,
            'szPassword': password,
            'isSaveId': 'false',
            'szScriptVar': 'oLoginRet',
            'szAction': '',
        }

        response = self._download_json(
            'https://login.afreecatv.com/app/LoginAction.php', None,
            'Logging in', data=urlencode_postdata(login_form))

        _ERRORS = {
            -4: 'Your account has been suspended due to a violation of our terms and policies.',
            -5: 'https://member.afreecatv.com/app/user_delete_progress.php',
            -6: 'https://login.afreecatv.com/membership/changeMember.php',
            -8: "Hello! AfreecaTV here.\nThe username you have entered belongs to \n an account that requires a legal guardian's consent. \nIf you wish to use our services without restriction, \nplease make sure to go through the necessary verification process.",
            -9: 'https://member.afreecatv.com/app/pop_login_block.php',
            -11: 'https://login.afreecatv.com/afreeca/second_login.php',
            -12: 'https://member.afreecatv.com/app/user_security.php',
            0: 'The username does not exist or you have entered the wrong password.',
            -1: 'The username does not exist or you have entered the wrong password.',
            -3: 'You have entered your username/password incorrectly.',
            -7: 'You cannot use your Global AfreecaTV account to access Korean AfreecaTV.',
            -10: 'Sorry for the inconvenience. \nYour account has been blocked due to an unauthorized access. \nPlease contact our Help Center for assistance.',
            -32008: 'You have failed to log in. Please contact our Help Center.',
        }

        result = int_or_none(response.get('RESULT'))
        if result != 1:
            error = _ERRORS.get(result, 'You have failed to log in.')
            raise ExtractorError(
                'Unable to login: %s said: %s' % (self.IE_NAME, error),
                expected=True)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        data = self._download_json(
            'https://api.m.afreecatv.com/station/video/a/view',
            video_id,
            headers={'Referer': url},
            data=urlencode_postdata({
                'nTitleNo': video_id,
                'nApiLevel': 10,
            }))['data']

        error_code = traverse_obj(data, ('code', {int}))
        if error_code == -6221:
            raise ExtractorError('The VOD does not exist', expected=True)
        elif error_code == -6205:
            raise ExtractorError('This VOD is private', expected=True)

        flag = traverse_obj(data, ('flag', {str}))
        if flag == 'PARTIAL_ADULT':
            self.report_warning(
                'In accordance with local laws and regulations, underage users are '
                'restricted from watching adult content. Only content suitable for all '
                f'ages will be downloaded. {self._login_hint(method="netrc")}')
        elif flag == 'ADULT':
            self.raise_login_required(
                'Only users older than 19 are able to watch this video', method='netrc')

        common_info = traverse_obj(data, {
            'title': ('title', {str}),
            'uploader': ('writer_nick', {str}),
            'uploader_id': ('bj_id', {str}),
            'duration': ('total_file_duration', {functools.partial(int_or_none, scale=1000)}),
            'thumbnail': ('thumb', {url_or_none}),
        })
        entries = []
        for file_num, file_element in enumerate(
                traverse_obj(data, ('files', lambda _, v: url_or_none(v['file']))), start=1):
            file_url = file_element['file']
            if determine_ext(file_url) == 'm3u8':
                formats = self._extract_m3u8_formats(
                    file_url, video_id, 'mp4', m3u8_id='hls',
                    note=f'Downloading part {file_num} m3u8 information')
            else:
                formats = [{
                    'url': file_url,
                    'format_id': 'http',
                }]

            entries.append({
                **common_info,
                'id': file_element.get('file_info_key') or f'{video_id}_{file_num}',
                'title': f'{common_info.get("title") or "Untitled"} (part {file_num})',
                'formats': formats,
                **traverse_obj(file_element, {
                    'duration': ('duration', {functools.partial(int_or_none, scale=1000)}),
                    'timestamp': ('file_start', {unified_timestamp}),
                })
            })
        if len(entries) == 1:
            return {
                **entries[0],
                'title': common_info.get('title'),
            }

        return self.playlist_result(entries, video_id, multi_video=True, **common_info)


class AfreecaTVLiveIE(AfreecaTVIE):  # XXX: Do not subclass from concrete IE

    IE_NAME = 'afreecatv:live'
    _VALID_URL = r'https?://play\.afreeca(?:tv)?\.com/(?P<id>[^/]+)(?:/(?P<bno>\d+))?'
    _TESTS = [{
        'url': 'https://play.afreecatv.com/pyh3646/237852185',
        'info_dict': {
            'id': '237852185',
            'ext': 'mp4',
            'title': '【 우루과이 오늘은 무슨일이? 】',
            'uploader': '박진우[JINU]',
            'uploader_id': 'pyh3646',
            'timestamp': 1640661495,
            'is_live': True,
        },
        'skip': 'Livestream has ended',
    }, {
        'url': 'http://play.afreeca.com/pyh3646/237852185',
        'only_matching': True,
    }, {
        'url': 'http://play.afreeca.com/pyh3646',
        'only_matching': True,
    }]

    _LIVE_API_URL = 'https://live.afreecatv.com/afreeca/player_live_api.php'

    _QUALITIES = ('sd', 'hd', 'hd2k', 'original')

    def _real_extract(self, url):
        broadcaster_id, broadcast_no = self._match_valid_url(url).group('id', 'bno')
        password = self.get_param('videopassword')

        info = self._download_json(self._LIVE_API_URL, broadcaster_id, fatal=False,
                                   data=urlencode_postdata({'bid': broadcaster_id})) or {}
        channel_info = info.get('CHANNEL') or {}
        broadcaster_id = channel_info.get('BJID') or broadcaster_id
        broadcast_no = channel_info.get('BNO') or broadcast_no
        password_protected = channel_info.get('BPWD')
        if not broadcast_no:
            raise ExtractorError(f'Unable to extract broadcast number ({broadcaster_id} may not be live)', expected=True)
        if password_protected == 'Y' and password is None:
            raise ExtractorError(
                'This livestream is protected by a password, use the --video-password option',
                expected=True)

        formats = []
        quality_key = qualities(self._QUALITIES)
        for quality_str in self._QUALITIES:
            params = {
                'bno': broadcast_no,
                'stream_type': 'common',
                'type': 'aid',
                'quality': quality_str,
            }
            if password is not None:
                params['pwd'] = password
            aid_response = self._download_json(
                self._LIVE_API_URL, broadcast_no, fatal=False,
                data=urlencode_postdata(params),
                note=f'Downloading access token for {quality_str} stream',
                errnote=f'Unable to download access token for {quality_str} stream')
            aid = traverse_obj(aid_response, ('CHANNEL', 'AID'))
            if not aid:
                continue

            stream_base_url = channel_info.get('RMD') or 'https://livestream-manager.afreecatv.com'
            stream_info = self._download_json(
                f'{stream_base_url}/broad_stream_assign.html', broadcast_no, fatal=False,
                query={
                    'return_type': channel_info.get('CDN', 'gcp_cdn'),
                    'broad_key': f'{broadcast_no}-common-{quality_str}-hls',
                },
                note=f'Downloading metadata for {quality_str} stream',
                errnote=f'Unable to download metadata for {quality_str} stream') or {}

            if stream_info.get('view_url'):
                formats.append({
                    'format_id': quality_str,
                    'url': update_url_query(stream_info['view_url'], {'aid': aid}),
                    'ext': 'mp4',
                    'protocol': 'm3u8',
                    'quality': quality_key(quality_str),
                })

        station_info = self._download_json(
            'https://st.afreecatv.com/api/get_station_status.php', broadcast_no,
            query={'szBjId': broadcaster_id}, fatal=False,
            note='Downloading channel metadata', errnote='Unable to download channel metadata') or {}

        return {
            'id': broadcast_no,
            'title': channel_info.get('TITLE') or station_info.get('station_title'),
            'uploader': channel_info.get('BJNICK') or station_info.get('station_name'),
            'uploader_id': broadcaster_id,
            'timestamp': unified_timestamp(station_info.get('broad_start')),
            'formats': formats,
            'is_live': True,
        }


class AfreecaTVUserIE(InfoExtractor):
    IE_NAME = 'afreecatv:user'
    _VALID_URL = r'https?://bj\.afreeca(?:tv)?\.com/(?P<id>[^/]+)/vods/?(?P<slug_type>[^/]+)?'
    _TESTS = [{
        'url': 'https://bj.afreecatv.com/ryuryu24/vods/review',
        'info_dict': {
            '_type': 'playlist',
            'id': 'ryuryu24',
            'title': 'ryuryu24 - review',
        },
        'playlist_count': 218,
    }, {
        'url': 'https://bj.afreecatv.com/parang1995/vods/highlight',
        'info_dict': {
            '_type': 'playlist',
            'id': 'parang1995',
            'title': 'parang1995 - highlight',
        },
        'playlist_count': 997,
    }, {
        'url': 'https://bj.afreecatv.com/ryuryu24/vods',
        'info_dict': {
            '_type': 'playlist',
            'id': 'ryuryu24',
            'title': 'ryuryu24 - all',
        },
        'playlist_count': 221,
    }, {
        'url': 'https://bj.afreecatv.com/ryuryu24/vods/balloonclip',
        'info_dict': {
            '_type': 'playlist',
            'id': 'ryuryu24',
            'title': 'ryuryu24 - balloonclip',
        },
        'playlist_count': 0,
    }]
    _PER_PAGE = 60

    def _fetch_page(self, user_id, user_type, page):
        page += 1
        info = self._download_json(f'https://bjapi.afreecatv.com/api/{user_id}/vods/{user_type}', user_id,
                                   query={'page': page, 'per_page': self._PER_PAGE, 'orderby': 'reg_date'},
                                   note=f'Downloading {user_type} video page {page}')
        for item in info['data']:
            yield self.url_result(
                f'https://vod.afreecatv.com/player/{item["title_no"]}/', AfreecaTVIE, item['title_no'])

    def _real_extract(self, url):
        user_id, user_type = self._match_valid_url(url).group('id', 'slug_type')
        user_type = user_type or 'all'
        entries = OnDemandPagedList(functools.partial(self._fetch_page, user_id, user_type), self._PER_PAGE)
        return self.playlist_result(entries, user_id, f'{user_id} - {user_type}')
