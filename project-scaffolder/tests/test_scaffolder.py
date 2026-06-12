import os
import shutil
import unittest
import tempfile
from scaffolder import ProjectScaffolder

class TestProjectScaffolder(unittest.TestCase):
    def setUp(self):
        self.scaffolder = ProjectScaffolder()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_supported_map(self):
        m = self.scaffolder.get_supported_map()
        self.assertIn("python", m)
        self.assertIn("javascript", m)
        self.assertIn("go", m)
        self.assertEqual(m["python"]["name"], "Python")

    def test_generate_python_fastapi(self):
        res = self.scaffolder.generate(
            lang="python",
            framework="fastapi",
            destination=self.temp_dir,
            project_name="test-fastapi-app",
            options={"docker": True, "docker_compose": True, "git_init": False}
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["project_name"], "test-fastapi-app")
        
        # Sprawdzenie obecności plików
        target_dir = res["target_directory"]
        self.assertTrue(os.path.exists(os.path.join(target_dir, "main.py")))
        self.assertTrue(os.path.exists(os.path.join(target_dir, "config.py")))
        self.assertTrue(os.path.exists(os.path.join(target_dir, "requirements.txt")))
        self.assertTrue(os.path.exists(os.path.join(target_dir, "Dockerfile")))
        self.assertTrue(os.path.exists(os.path.join(target_dir, "docker-compose.yml")))
        self.assertTrue(os.path.exists(os.path.join(target_dir, ".gitignore")))

    def test_generate_js_express(self):
        res = self.scaffolder.generate(
            lang="javascript",
            framework="express",
            destination=self.temp_dir,
            project_name="express-api",
            options={"docker": True, "license": True, "git_init": False}
        )
        self.assertTrue(res["success"])
        target_dir = res["target_directory"]
        self.assertTrue(os.path.exists(os.path.join(target_dir, "package.json")))
        self.assertTrue(os.path.exists(os.path.join(target_dir, "tsconfig.json")))
        self.assertTrue(os.path.exists(os.path.join(target_dir, "src/index.ts")))
        self.assertTrue(os.path.exists(os.path.join(target_dir, "LICENSE")))

    def test_generate_go_gin(self):
        res = self.scaffolder.generate(
            lang="go",
            framework="gin",
            destination=self.temp_dir,
            project_name="go-service",
            options={"github_actions": True, "git_init": False}
        )
        self.assertTrue(res["success"])
        target_dir = res["target_directory"]
        self.assertTrue(os.path.exists(os.path.join(target_dir, "main.go")))
        self.assertTrue(os.path.exists(os.path.join(target_dir, "go.mod")))
        self.assertTrue(os.path.exists(os.path.join(target_dir, ".github/workflows/ci.yml")))

    def test_file_exists_error_prevents_overwrite(self):
        # Generujemy pierwszy raz
        self.scaffolder.generate("go", "gin", self.temp_dir, "duplicate-app", {"git_init": False})
        
        # Próba wygenerowania drugi raz bez opcji overwrite powinna rzucić błąd
        with self.assertRaises(FileExistsError):
            self.scaffolder.generate("go", "gin", self.temp_dir, "duplicate-app", {"git_init": False})

    def test_overwrite_option_forces_replace(self):
        # Pierwsze generowanie
        res1 = self.scaffolder.generate("go", "gin", self.temp_dir, "overwrite-app", {"git_init": False})
        path_test_file = os.path.join(res1["target_directory"], "custom_leak.txt")
        with open(path_test_file, "w") as f:
            f.write("junk data")

        # Drugie generowanie z overwrite=True
        res2 = self.scaffolder.generate("go", "gin", self.temp_dir, "overwrite-app", {"overwrite": True, "git_init": False})
        self.assertTrue(res2["success"])
        
        # Plik custom_leak.txt powinien zniknąć (cały folder nadpisany)
        self.assertFalse(os.path.exists(path_test_file))

if __name__ == "__main__":
    unittest.main()
