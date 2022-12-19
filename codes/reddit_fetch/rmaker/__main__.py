import click

@click.command()
@click.option("--comm/", "-c/", is_flag=True, default=False, help="fetch comments by post ids")
@click.argument("start", nargs=1)
@click.argument("end", nargs=1)
@click.argument("channel", nargs=1)
def make_reddit(comm, start, end, channel):  # 
    """build text file from reddit"""
    from rmaker.maker import RedditMaker

    r = RedditMaker(start, end)

    if comm:
        r.fetch_comment_by_post(channel)
    else:
        r.fetch_text(channel, 'p')



if __name__ == '__main__':
    make_reddit()
