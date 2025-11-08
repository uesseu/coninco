import discord
from urllib.request import Request, urlopen
from discord.ext import tasks
from pathlib import Path
import json
import sys
from calender import Calender, parse_calender
from datetime import datetime
from argparse import ArgumentParser


parser = ArgumentParser(
    prog='CONINCO',
    description='Bot of Discord for frieds or family'
)
parser.add_argument(
    '-c', '--config', default='config.json',
    help='Path of config file. If "-", the file will be read from.'
)
parser.add_argument(
    '-d', '--debug', action='store_true',
    help='Debug mode'
)


args = parser.parse_args()


debug = args.debug
config = json.loads(
    str(sys.stdin.read().replace('\n', '').strip())
    if args.config == '-' else Path(args.config).read_text()
)

for directory in config['directory']:
    path: Path = Path('.') / directory
    if not path.exists():
        path.mkdir()


class CoNinco(discord.Client):
    user: discord.ClientUser

    async def on_ready(self):
        self.first_time = True
        if not debug:
            loop.start(self)
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')


    async def on_message_delete(self, message):
        logpath = Path(config['directory']['log']) / str(message.guild.id)
        if not logpath.exists():
            logpath.mkdir()
        with open(logpath / (str(message.channel.id) + '.txt'), 'a') as fp:
            fp.write(f'''# {message.author.nick}: {message.author.name}: {message.author.id}: DELETED
{datetime.now()}''')

    async def on_message(self, message):
        # Save message or attachments
        logpath = Path(config['directory']['log']) / str(message.guild.id)
        if not logpath.exists():
            logpath.mkdir()
        with open(logpath / (str(message.channel.id) + '.txt'), 'a') as fp:
            fp.write(f'''# {message.author.nick}: {message.author.name}: {message.author.id}
{datetime.now()}
{'\n'.join(['  ' + m + '\n' for m in message.content.split('\n')])}''')
        if len(message.attachments) > 0:
            for attachment in message.attachments:
                attpath = logpath / datetime.now().strftime('%Y%m%d')
                if not attpath.exists():
                    attpath.mkdir()
                fname = attachment.to_dict()['filename']
                while True:
                    if (attpath / fname).exists():
                        fname = '_' + fname
                    else:
                        break
                with open(attpath / fname, 'wb') as fp:
                    fp.write(await attachment.read())

        if client.user in message.mentions: # 話しかけられたかの判定
            reply = f'{message.author.mention} 呼んだ？まだ作成中ですよ？'
            await message.channel.send(reply)

        events = Events(message)
        await events.run()


class EventsBase:
    def __init__(self, message: discord.Message):
        self.message = message
        self.names = [n for n in self.__dir__() if n.startswith('on_')]

    async def run(self, length: int = 3):
        for n in self.names:
            if self.message.content[1:].startswith(n[3:length + 3]):
                await self.__getattribute__(n)()


class Events(EventsBase):
    async def on_calender(self):
        options = self.message.content.split(' ')
        to_delete = 'del' in options
        last_day = 10
        for n in options:
            if n.isdigit():
                last_day = int(n)
        if to_delete:
            await self.message.delete()
        for conf in config['calender']['data']:
            await put_calender(
                self.message.channel,
                conf,
                (0, last_day),
                False,
                delete_after=15 if to_delete else None
            )

    async def on_delete(self):
        options = self.message.content.split(' ')
        num = 1
        for n in options:
            if n.isdigit():
                num = int(n)
        async for n in self.message.channel.history():
            if num == 0:
                break
            await n.delete()
            num -= 1

    async def on_reserve(self):
        pass


def get_calender(url, path, overwrite=False):
    ''' Gets google calender from config file.
    url: str
        URL of ica file.
    path: str | Path
        Path of cache
    conf: dict
        Individual config dict of google calender.
    '''
    if overwrite or not path.exists():
        with urlopen(Request(url)) as f:
            data = f.read().decode()
        path.write_text(data)
    else:
        data = path.read_text()
    return data


def make_oneline_calender(
    cal: Calender, name: str, days: tuple[int, int]
) -> discord.Embed | None:
    if days[0] < cal.from_now() < days[1]:
        embed = discord.Embed(
            title='🗓️  '+cal.summary,
            color=0x00ff00,
            description=cal.description,
            url="https://www.google.com/calendar/render?"
            "action=TEMPLATE&"
            f"text={cal.summary}&dates={cal.start_raw}/"
            f"{cal.end_raw}&details={cal.description}"
        )
        embed.add_field(
            name="Person",
            value=name,
            inline=False
        )
        embed.add_field(
            name="From",
            value=str(cal.start.strftime('%Y/%m/%d(%a) %H:%M'))
        )
        embed.add_field(
            name="To",
            value=str(cal.end.strftime('%Y/%m/%d(%a) %H:%M'))
        )
        return embed
    return None


async def put_calender(channel, conf, days, overwrite, **kwargs):
    ''' Put timeline newest calender.
    It puts several items in one calender.

    conf: dict
        Individual config dict of google calender.
    days: list[int]
        Days from and to.
    overwrite: bool
        Download and overwrite google calender or not.
    '''
    path = Path(config['directory']['calender']) / conf['name']
    url = conf['url']
    for n in parse_calender(get_calender(url, path, overwrite)):
        one_calender = make_oneline_calender(Calender(n), conf['name'], days)
        if one_calender:
            await channel.send(embed=one_calender, **kwargs)


@tasks.loop(hours=24)
async def loop(client):
    try:
        for conf in config['calender']['data']:
            await put_calender(
                await client.fetch_channel(config['channel']['calender']),
                conf,
                (0, 9) if client.first_time else (9, 10),
                True
            )
            client.first_time = False
    except StopIteration as er:
        print(er)

intents = discord.Intents.default()
intents.message_content = True
client = CoNinco(intents=intents)
client.run(config['token'])
