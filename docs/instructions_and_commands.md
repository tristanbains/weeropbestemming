## TO DO

* docs niet in app.py build
* instructies git remote zodat niet overschrijven
* pip freeze m requirements.txt te overschrijven
* package development instructies
* GH actions instructies en file in scaffold.sh, creeren en schedule commenten, paar standaard files, bv download en train model, allemaal commented out
* add packages in requirements_dex.txt for cookiecutter aan eigen requirements.txt, zie link
* add and populate environment file, contains url, etc.
* add 404.html

## Copy files

## Scaffold

```
chmod +x scaffold_Flask_pseo.sh
./scaffold_Flask_pseo.sh_gitignore.sh
```

## Docker

### build

```
docker compose down
docker compose build --no-cache
```

### run

Terminal 1:
```
docker compose up -d
```

Terminal 2:
Watch CSS file:

```
npm run build-css
```

In terminal 1, run `python app.py build` to build static files in build folder via compose:

```
docker compose run web build
```

## Git

### clone en init

```
sudo rm -r .git
git init
```

[Stackoverflow reset git in folder](https://stackoverflow.com/questions/22067873/troubleshooting-misplaced-git-directory-nothing-to-commit)

### Commit en push

```
git status
git add .
git commit -m "some message"
git push
```

### remote origin

```
git remote -v
```

TO DO: ssh instructies

### branches etc.

## Run development server

cd into build folder, then

```
python3 -m http.server 8111
```

to serve on `localhost:8111`

## Create custom package

Open console in Jupyter, then

`cookiecutter https://github.com/audreyfeldroy/cookiecutter-pypackage.git`

[Cookiecutter docs](https://cookiecutter-pypackage.readthedocs.io/en/latest/readme.html#quickstart)