# installing

1) install conda-lock

       conda install conda-lock mamba

2) generate a new conda lock file if environment.yml has changed:

       conda-lock -f environment.yml -p linux-64

   or win-64 or macos-64

3) create and activate the new environment:

      mamba create --name dash --file conda-linux-64.lock
      mamba activate dash
      pip install -r requirements.txt

4) start the app and browse localhost:8050

     python app.py

5) to install the pre-commit hooks

     pre-commit install

6) to check in ignoring the pre-commit failures

     git commit --no-verify
