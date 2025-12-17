# Roundcube Embedded

> [!WARNING]
> This project has been made stricly in an educational and academic context and do not intend to harm any third party.

Roundcube Embedded is simple web page embedding Roundcube Webmail client in an iframe to provide additional functionalities to the page such as date/time and a timer for a crisis cell simulation.

You can also find two resources pages for the environement that are independant of the webmail client :

- A timeout page at `/site/timeout/index.html`
- A fake hacker page at `/site/fake-page/index.html`

## Installation

> [!HINT]
> Check that docker is installed and running on your system.

Download the docker compose file:

```bash
curl -O https://raw.githubusercontent.com/MorganKryze/roundcube-embedded/main/docker/compose.yml
```

I use pangolin to route web traffic to my docker containers, so you may need to adapt the `networks` section of the compose file to fit your own configuration. also, you may not need for the watchtower labels if you do not run it in your environment.

Then start the container:

```bash
docker-compose up -d
```

## Licence

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
