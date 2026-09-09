"""Keep generated test studies, meshes and runs separate from the user's data."""
import os, tempfile
os.environ['FEAR_DATA_DIR']=tempfile.mkdtemp(prefix='fea-r-tests-')
