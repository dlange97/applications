import os
import shutil
import json
import subprocess

class ProjectScaffolder:
    """
    Zaawansowany lokalny generator projektów dla najpopularniejszych języków i frameworków.
    """
    def __init__(self):
        self.supported_languages = {
            "python": {
                "name": "Python",
                "frameworks": {
                    "fastapi": "FastAPI",
                    "flask": "Flask",
                    "django": "Django (Minimalistyczny szablon)"
                }
            },
            "javascript": {
                "name": "JavaScript/TypeScript",
                "frameworks": {
                    "react": "React (Vite)",
                    "nextjs": "Next.js (App Router)",
                    "express": "Express.js (Node Backend)",
                    "nestjs": "NestJS Skeleton"
                }
            },
            "php": {
                "name": "PHP",
                "frameworks": {
                    "laravel": "Laravel Skeleton",
                    "symfony": "Symfony Skeleton"
                }
            },
            "java": {
                "name": "Java",
                "frameworks": {
                    "springboot": "Spring Boot (Maven)"
                }
            },
            "go": {
                "name": "Go",
                "frameworks": {
                    "gin": "Gin Gonic",
                    "fiber": "Go Fiber"
                }
            }
        }

    def get_supported_map(self):
        return self.supported_languages

    def generate(self, lang, framework, destination, project_name, options=None):
        """
        Główna metoda tworząca strukturę projektu na podstawie języka i frameworku.
        """
        if options is None:
            options = {}

        project_name = project_name.strip() or "my-scaffolded-app"
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_name).lower()
        
        target_dir = os.path.abspath(os.path.join(destination, safe_name))
        
        # Przygotowanie folderu docelowego
        if os.path.exists(target_dir):
            if options.get("overwrite", False):
                shutil.rmtree(target_dir)
            else:
                raise FileExistsError(f"Folder docelowy '{target_dir}' już istnieje. Zaznacz opcję nadpisania r.", target_dir)

        os.makedirs(target_dir, exist_ok=True)
        created_files = []

        files_to_write = {}

        # ----------------------------------------------------
        # PYTHON - FastAPI
        # ----------------------------------------------------
        if lang == "python" and framework == "fastapi":
            files_to_write.update({
                "requirements.txt": "fastapi>=0.110.0\nuvicorn>=0.28.0\npydantic>=2.6.0\npydantic-settings>=2.0.0\n",
                "config.py": self._get_fastapi_config(),
                "main.py": self._get_fastapi_main(),
                "README.md": self._get_readme(project_name, "Python + FastAPI", "Uruchomienie lokalne:\n```bash\npip install -r requirements.txt\nuvicorn main:app --reload\n```\nNastępnie otwórz przeglądarkę na: `http://127.0.0.1:8000/docs`"),
            })
            if options.get("docker", False):
                files_to_write["Dockerfile"] = self._get_dockerfile_python("main:app", 8000, "uvicorn main:app --host 0.0.0.0 --port 8000")

        # ----------------------------------------------------
        # PYTHON - Flask
        # ----------------------------------------------------
        elif lang == "python" and framework == "flask":
            files_to_write.update({
                "requirements.txt": "Flask>=3.0.0\n",
                "app.py": self._get_flask_app(),
                "README.md": self._get_readme(project_name, "Python + Flask", "Uruchomienie lokalne:\n```bash\npip install -r requirements.txt\npython app.py\n```\nOtwórz adres: `http://127.0.0.1:5000`"),
            })
            if options.get("docker", False):
                files_to_write["Dockerfile"] = self._get_dockerfile_python("app:app", 5000, "python app.py")

        # ----------------------------------------------------
        # PYTHON - Django
        # ----------------------------------------------------
        elif lang == "python" and framework == "django":
            files_to_write.update({
                "requirements.txt": "Django>=5.0.0\n",
                f"{safe_name}/__init__.py": "",
                f"{safe_name}/settings.py": self._get_django_settings(safe_name),
                f"{safe_name}/urls.py": self._get_django_urls(safe_name),
                f"{safe_name}/wsgi.py": f'import os\nfrom django.core.wsgi import get_wsgi_application\nos.environ.setdefault("DJANGO_SETTINGS_MODULE", "{safe_name}.settings")\napplication = get_wsgi_application()\n',
                "manage.py": self._get_django_manage(safe_name),
                "README.md": self._get_readme(project_name, "Python + Django (Minimal)", "Uruchomienie lokalne:\n```bash\npip install -r requirements.txt\npython manage.py migrate\npython manage.py runserver 0.0.0.0:8000\n```"),
            })
            if options.get("docker", False):
                files_to_write["Dockerfile"] = self._get_dockerfile_python("manage", 8000, "python manage.py runserver 0.0.0.0:8000")

        # ----------------------------------------------------
        # JS/TS - React (Vite)
        # ----------------------------------------------------
        elif lang == "javascript" and framework == "react":
            files_to_write.update({
                "package.json": json.dumps({
                    "name": safe_name,
                    "private": True,
                    "version": "1.0.0",
                    "type": "module",
                    "scripts": {
                        "dev": "vite",
                        "build": "tsc && vite build",
                        "preview": "vite preview"
                    },
                    "dependencies": {
                        "react": "^18.3.1",
                        "react-dom": "^18.3.1"
                    },
                    "devDependencies": {
                        "@types/react": "^18.3.3",
                        "@types/react-dom": "^18.3.0",
                        "@vitejs/plugin-react": "^4.3.1",
                        "typescript": "^5.2.2",
                        "vite": "^5.2.11"
                    }
                }, indent=2),
                "tsconfig.json": self._get_tsconfig_react(),
                "vite.config.ts": "import { defineConfig } from 'vite';\nimport react from '@vitejs/plugin-react';\n\nexport default defineConfig({\n  plugins: [react()],\n  server: { port: 3000 }\n});\n",
                "index.html": self._get_react_index_html(project_name),
                "src/main.tsx": "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\nimport './index.css';\n\nReactDOM.createRoot(document.getElementById('root')!).render(\n  <React.StrictMode>\n    <App />\n  </React.StrictMode>,\n);\n",
                "src/index.css": "body {\n  margin: 0;\n  font-family: system-ui, -apple-system, sans-serif;\n  background-color: #0f172a;\n  color: #f8fafc;\n}\n",
                "src/App.tsx": self._get_react_app_tsx(project_name),
                "README.md": self._get_readme(project_name, "React (Vite + TS)", "Uruchomienie lokalne:\n```bash\nnpm install\nnpm run dev\n```\nOtwórz adres: `http://localhost:3000`"),
            })
            if options.get("docker", False):
                files_to_write["Dockerfile"] = self._get_dockerfile_node("npm run build", "dist", 80)

        # ----------------------------------------------------
        # JS/TS - Next.js
        # ----------------------------------------------------
        elif lang == "javascript" and framework == "nextjs":
            files_to_write.update({
                "package.json": json.dumps({
                    "name": safe_name,
                    "version": "1.0.0",
                    "private": True,
                    "scripts": {
                        "dev": "next dev",
                        "build": "next build",
                        "start": "next start"
                    },
                    "dependencies": {
                        "next": "^14.2.3",
                        "react": "^18.3.1",
                        "react-dom": "^18.3.1"
                    },
                    "devDependencies": {
                        "typescript": "^5.2.2",
                        "@types/node": "^20.11.0",
                        "@types/react": "^18.3.3",
                        "@types/react-dom": "^18.3.0"
                    }
                }, indent=2),
                "tsconfig.json": self._get_tsconfig_nextjs(),
                "next.config.js": "/** @type {import('next').NextConfig} */\nconst nextConfig = {\n  reactStrictMode: true,\n};\nmodule.exports = nextConfig;\n",
                "src/app/layout.tsx": "import React from 'react';\nimport './globals.css';\n\nexport const metadata = {\n  title: '" + project_name + "',\n  description: 'Zainicjalizowano za pomocą Project Scaffolder Pro',\n};\n\nexport default function RootLayout({ children }: { children: React.ReactNode }) {\n  return (\n    <html lang=\"pl\">\n      <body>{children}</body>\n    </html>\n  );\n}\n",
                "src/app/globals.css": "body {\n  margin: 0;\n  color: #333;\n  background: #fdfdfd;\n  font-family: sans-serif;\n}\n",
                "src/app/page.tsx": self._get_nextjs_page_tsx(project_name),
                "README.md": self._get_readme(project_name, "Next.js (App Router)", "Uruchomienie lokalne:\n```bash\nnpm install\nnpm run dev\n```\nOtwórz: `http://localhost:3000`"),
            })

        # ----------------------------------------------------
        # JS/TS - Express
        # ----------------------------------------------------
        elif lang == "javascript" and framework == "express":
            files_to_write.update({
                "package.json": json.dumps({
                    "name": safe_name,
                    "version": "1.0.0",
                    "main": "dist/index.js",
                    "scripts": {
                        "build": "tsc",
                        "start": "node dist/index.js",
                        "dev": "ts-node src/index.ts"
                    },
                    "dependencies": {
                        "express": "^4.19.2",
                        "cors": "^2.8.5",
                        "dotenv": "^16.4.5"
                    },
                    "devDependencies": {
                        "typescript": "^5.2.2",
                        "@types/express": "^4.17.21",
                        "@types/node": "^20.11.0",
                        "@types/cors": "^2.8.17",
                        "ts-node": "^10.9.2"
                    }
                }, indent=2),
                "tsconfig.json": self._get_tsconfig_node(),
                "src/index.ts": self._get_express_index_ts(project_name),
                ".env": "PORT=5000\nNODE_ENV=development\nDATABASE_URL=mongodb://localhost:27017/dbname\n",
                "README.md": self._get_readme(project_name, "Express.js API", "Uruchomienie lokalne:\n```bash\nnpm install\nnpm run dev\n```\nEndpoint testowy: `http://localhost:5000/api/health`"),
            })
            if options.get("docker", False):
                files_to_write["Dockerfile"] = self._get_dockerfile_node_express(5000)

        # ----------------------------------------------------
        # JS/TS - NestJS
        # ----------------------------------------------------
        elif lang == "javascript" and framework == "nestjs":
            files_to_write.update({
                "package.json": json.dumps({
                    "name": safe_name,
                    "version": "1.0.0",
                    "license": "UNLICENSED",
                    "scripts": {
                        "build": "nest build",
                        "start": "nest start",
                        "start:dev": "nest start --watch"
                    },
                    "dependencies": {
                        "@nestjs/common": "^10.0.0",
                        "@nestjs/core": "^10.0.0",
                        "@nestjs/platform-express": "^10.0.0",
                        "reflect-metadata": "^0.1.13",
                        "rxjs": "^7.8.1"
                    },
                    "devDependencies": {
                        "@nestjs/cli": "^10.0.0",
                        "@nestjs/schematics": "^10.0.0",
                        "@types/node": "^20.11.0",
                        "typescript": "^5.2.2"
                    }
                }, indent=2),
                "tsconfig.json": self._get_tsconfig_node(),
                "nest-cli.json": json.dumps({"language": "ts", "sourceRoot": "src", "collection": "@nestjs/schematics"}, indent=2),
                "src/main.ts": "import { NestFactory } from '@nestjs/core';\nimport { AppModule } from './app.module';\n\nasync function bootstrap() {\n  const app = await NestFactory.create(AppModule);\n  await app.listen(3000);\n  console.log('NestJS jest uruchomiony na: http://localhost:3000');\n}\nbootstrap();\n",
                "src/app.module.ts": "import { Module } from '@nestjs/common';\nimport { AppController } from './app.controller';\nimport { AppService } from './app.service';\n\n@Module({\n  imports: [],\n  controllers: [AppController],\n  providers: [AppService],\n})\nexport class AppModule {}\n",
                "src/app.controller.ts": "import { Controller, Get } from '@nestjs/common';\nimport { AppService } from './app.service';\n\n@Controller()\nexport class AppController {\n  constructor(private readonly appService: AppService) {}\n\n  @Get()\n  getHello(): string {\n    return this.appService.getHello();\n  }\n}\n",
                "src/app.service.ts": "import { Injectable } from '@nestjs/common';\n\n@Injectable()\nexport class AppService {\n  getHello(): string {\n    return 'Witaj w NestJS! Usługa działa prawidłowo.';\n  }\n}\n",
                "README.md": self._get_readme(project_name, "NestJS API", "Uruchomienie lokalne:\n```bash\nnpm install\nnpm run start:dev\n```\nOtwórz adres: `http://localhost:3000`"),
            })

        # ----------------------------------------------------
        # PHP - Laravel
        # ----------------------------------------------------
        elif lang == "php" and framework == "laravel":
            files_to_write.update({
                "composer.json": json.dumps({
                    "name": f"user/{safe_name}",
                    "type": "project",
                    "description": "Zainicjalizowany Laravel za pomoca Project Scaffolder.",
                    "require": {
                        "php": "^8.2",
                        "laravel/framework": "^11.0"
                    },
                    "autoload": {
                        "psr-4": {
                            "App\\": "app/"
                        }
                    }
                }, indent=2),
                "app/Http/Controllers/HomeController.php": self._get_laravel_controller(),
                "routes/web.php": "<?php\n\nuse Illuminate\\Support\\Facades\\Route;\nuse App\\Http\\Controllers\\HomeController;\n\nRoute::get('/', [HomeController::class, 'index']);\n",
                "config/app.php": "<?php\nreturn [\n    'name' => env('APP_NAME', '" + project_name + "'),\n    'env' => env('APP_ENV', 'production'),\n    'debug' => (bool) env('APP_DEBUG', false),\n    'url' => env('APP_URL', 'http://localhost'),\n];\n",
                "public/index.php": "<?php\n\nuse Illuminate\\Contracts\\Http\\Kernel;\nuse Illuminate\\Http\\Request;\n\ndefine('LARAVEL_START', microtime(true));\n\nrequire __DIR__.'/../vendor/autoload.php';\n\necho \"<h1>Witaj w Symfony/Laravel Mock (Brak pełnej bazy PHP)</h1>\";\necho \"<p>Serwer działa. Dołącz vendor/autoload.php...</p>\";\n",
                "README.md": self._get_readme(project_name, "Laravel PHP Skeleton", "Uruchomienie lokalne:\n```bash\ncomposer install\nphp artisan serve\n```\nNastępnie wejdź na `http://127.0.0.1:8000`"),
            })

        # ----------------------------------------------------
        # PHP - Symfony
        # ----------------------------------------------------
        elif lang == "php" and framework == "symfony":
            files_to_write.update({
                "composer.json": json.dumps({
                    "name": f"user/{safe_name}",
                    "type": "project",
                    "description": "Symfony starter",
                    "require": {
                        "php": "^8.2",
                        "symfony/framework-bundle": "^7.0"
                    },
                    "autoload": {
                        "psr-4": {
                            "App\\": "src/"
                        }
                    }
                }, indent=2),
                "src/Controller/HomeController.php": self._get_symfony_controller(),
                "src/Kernel.php": "<?php\nnamespace App;\nuse Symfony\\Bundle\\FrameworkBundle\\Kernel\\MicroKernelTrait;\nuse Symfony\\Component\\HttpKernel\\Kernel as BaseKernel;\n\nclass Kernel extends BaseKernel {\n    use MicroKernelTrait;\n}\n",
                "config/routes.yaml": "home_controller:\n    path: /\n    controller: App\\Controller\\HomeController::index\n",
                "public/index.php": "<?php\nuse App\\Kernel;\nrequire_once dirname(__DIR__).'/vendor/autoload_runtime.php';\nreturn function (array $context) {\n    return new Kernel($context['APP_ENV'], (bool) $context['APP_DEBUG']);\n};\n",
                "README.md": self._get_readme(project_name, "Symfony Starter Framework", "Uruchomienie lokalne:\n```bash\ncomposer install\nsymfony server:start\n```"),
            })

        # ----------------------------------------------------
        # JAVA - Spring Boot
        # ----------------------------------------------------
        elif lang == "java" and framework == "springboot":
            package_path = "src/main/java/com/example/demo"
            files_to_write.update({
                "pom.xml": self._get_springboot_pom(safe_name),
                f"{package_path}/DemoApplication.java": self._get_springboot_main(),
                f"{package_path}/controller/HelloController.java": self._get_springboot_controller(),
                "src/main/resources/application.properties": "server.port=8080\nspring.application.name=" + safe_name + "\n",
                "README.md": self._get_readme(project_name, "Spring Boot (Maven Java)", "Kompilacja i uruchomienie:\n```bash\n./mvnw clean package\n./mvnw spring-boot:run\n```\nEndpoint testowy pod adresem: `http://localhost:8080/`"),
            })

        # ----------------------------------------------------
        # GO - Gin
        # ----------------------------------------------------
        elif lang == "go" and framework == "gin":
            files_to_write.update({
                "go.mod": f"module {safe_name}\n\ngo 1.21\n\nrequire github.com/gin-gonic/gin v1.9.1\n",
                "main.go": self._get_go_gin_main(project_name),
                "README.md": self._get_readme(project_name, "Go + Gin Gonic API", "Uruchomienie lokalne:\n```bash\ngo mod tidy\ngo run main.go\n```\nPort nasłuchu to: `8080`"),
            })
            if options.get("docker", False):
                files_to_write["Dockerfile"] = self._get_dockerfile_go(8080)

        # ----------------------------------------------------
        # GO - Fiber
        # ----------------------------------------------------
        elif lang == "go" and framework == "fiber":
            files_to_write.update({
                "go.mod": f"module {safe_name}\n\ngo 1.21\n\nrequire github.com/gofiber/fiber/v2 v2.51.0\n",
                "main.go": self._get_go_fiber_main(project_name),
                "README.md": self._get_readme(project_name, "Go + Fiber Backend", "Uruchomienie lokalne:\n```bash\ngo mod tidy\ngo run main.go\n```\nAdres serwera: `http://localhost:3000`"),
            })
            if options.get("docker", False):
                files_to_write["Dockerfile"] = self._get_dockerfile_go(3000)

        else:
            raise ValueError(f"Niewspierany język/framework: {lang} / {framework}")

        # ----------------------------------------------------
        # EXTRA DODATKI (Opcjonalne)
        # ----------------------------------------------------
        # .github/workflows/ci.yml
        if options.get("github_actions", False):
            files_to_write[".github/workflows/ci.yml"] = self._get_github_actions_ci(lang)

        # LICENSE - MIT
        if options.get("license", False):
            files_to_write["LICENSE"] = f"MIT License\n\nCopyright (c) 2026 {options.get('author', 'Developer')}\n\nPermission is hereby granted, free of charge, to any person obtaining a copy..."

        # Docker Compose
        if options.get("docker_compose", False):
            files_to_write["docker-compose.yml"] = self._get_docker_compose_yml(lang, framework)

        # .gitignore
        files_to_write[".gitignore"] = self._get_gitignore(lang)

        # ZAPIS WSZYSTKICH PLIKÓW
        for relative_path, content in files_to_write.items():
            full_path = os.path.join(target_dir, relative_path)
            # Tworzenie folderów nadrzędnych
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            created_files.append(relative_path)

        # Inicjalizacja repozutorium GIT jeśli wybrano
        git_status = "Nie wybrano git init"
        if options.get("git_init", False):
            try:
                subprocess.run(["git", "init"], cwd=target_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["git", "add", "."], cwd=target_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["git", "commit", "-m", "Initial commit from Project Scaffolder Pro"], cwd=target_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                git_status = "Pomyślnie zainicjalizowano repozytorium GIT i utworzono Initial Commit!"
            except Exception as e:
                git_status = f"Błąd podczas init GIT: {str(e)}"

        return {
            "success": True,
            "project_name": project_name,
            "target_directory": target_dir,
            "created_files": created_files,
            "git_status": git_status
        }

    # ----------------------------------------------------
    # SZABLONY ZAWARTOŚCI PLIKÓW
    # ----------------------------------------------------

    def _get_readme(self, title, technology, start_command):
        return f"""# {title} 🚀

System wygenerowany automatycznie za pomocą profesjonalnego narzędzia **Project Scaffolder Pro**.

## 💻 Technologia
Ten projekt został oparty o szablon **{technology}** stworzony z zachowaniem najlepszych praktyk architektonicznych i bezpieczeństwa.

## 🛠️ Instrukcja uruchomienia
{start_command}

## 📁 Zawartość struktury
- `Dockerfile` / `docker-compose.yml` (Jeśli zaznaczono opcję konteneryzacji)
- `.gitignore` dedykowany pod specyfikę używanego środowiska.
- Narzędzia CI/CD i konfiguracje lintera/formatera.

---
*Created dynamically in 2026.*
"""

    def _get_gitignore(self, lang):
        if lang == "python":
            return "__pycache__/\n*.py[cod]\n*$py.class\n.venv/\nvenv/\nENV/\n.env\n.pytest_cache/\n"
        elif lang == "javascript":
            return "node_modules/\ndist/\n.next/\nout/\n.env*.local\n.env\n*.log\n"
        elif lang == "go":
            return "*.exe\n*.exe~\n*.dll\n*.so\n*.dylib\n*.test\n*.out\nbin/\n"
        elif lang == "java":
            return "target/\n*.class\n*.jar\n*.war\n*.ear\n.idea/\n*.iml\n.gradle/\nbuild/\n"
        elif lang == "php":
            return "vendor/\n.env\n.phpunit.result.cache\nHomestead.json\nHomestead.yaml\n"
        return "node_modules/\n.env\n*.log\n"

    def _get_fastapi_config(self):
        return """from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "FastAPI Service Pro"
    admin_email: str = "admin@example.com"
    items_per_user: int = 50

    class Config:
        env_file = ".env"

settings = Settings()
"""

    def _get_fastapi_main(self):
        return """from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="FastAPI Service Pro",
    description="Profesjonalny szkielet projektu FastAPI zintegrowany z CORSRouter i standardem OpenAPI.",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "FastAPI Web Service",
        "docs_url": "/docs",
        "endpoints": ["/api/v1/health", "/api/v1/items"]
    }

@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy", "database": "connected", "cache": "connected"}

@app.get("/api/v1/items/{item_id}")
def read_item(item_id: int, q: str = None):
    if item_id < 1 or item_id > 1000:
        raise HTTPException(status_code=404, detail="Item not found inside database")
    return {"item_id": item_id, "query_param": q, "name": f"Produkt o ID {item_id}"}
"""

    def _get_flask_app(self):
        return """from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "app": "Flask Microservice Pro",
        "api_endpoints": [
            "GET /api/health",
            "POST /api/echo"
        ],
        "status": "working"
    })

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "UP",
        "environment": "development",
        "features": {
            "auth": True,
            "metrics": False
        }
    })

@app.route("/api/echo", methods=["POST"])
def echo_payload():
    data = request.get_json() or {}
    return jsonify({
        "received_data": data,
        "message": "Payload returned successfully"
    })

if __name__ == "__main__":
    print("Uruchamianie lokalnego Flask na http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
"""

    def _get_django_settings(self, app_name):
        return f"""import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-custom-key-for-project-scaffolder-development'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = '{app_name}.urls'
WSGI_APPLICATION = '{app_name}.wsgi.application'

DATABASES = {{
    'default': {{
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }}
}}

LANGUAGE_CODE = 'pl-pl'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
"""

    def _get_django_urls(self, app_name):
        return """from django.contrib import admin
from django.urls import path
from django.http import JsonResponse

def home_view(request):
    return JsonResponse({
        "message": "Witaj w Django (Minimalistyczna architektura r.)",
        "admin_panel": "/admin/",
        "endpoints": ["/api/health/"]
    })

def health_view(request):
    return JsonResponse({"status": "OK", "database": "sqlite3"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view),
    path('api/health/', health_view),
]
"""

    def _get_django_manage(self, app_name):
        return f"""#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{app_name}.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed or active inside virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
"""

    def _get_tsconfig_react(self):
        return """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
"""

    def _get_react_index_html(self, title):
        return f"""<!doctype html>
<html lang="pl">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""

    def _get_react_app_tsx(self, title):
        return """import React, { useState } from 'react';

export default function App() {
  const [count, setCount] = useState(0);

  return (
    <div style={{ maxWidth: '800px', margin: '40px auto', padding: '20px', textAlign: 'center' }}>
      <h1 style={{ color: '#60a5fa', fontSize: '2.5rem' }}>""" + title + """ 🚀</h1>
      <p style={{ fontSize: '1.2rem', color: '#94a3b8' }}>
        Projekt React sformatowany za pomocą Vite oraz TypeScript.
      </p>
      
      <div style={{ background: '#1e293b', border: '1px solid #334155', padding: '30px', borderRadius: '12px', marginTop: '30px' }}>
        <h3 style={{ margin: '0 0 15px', color: '#f8fafc' }}>Interaktywny Stan Komponentu</h3>
        <p style={{ fontSize: '2rem', color: '#38bdf8', margin: '15px 0' }}>{count}</p>
        <button 
          onClick={() => setCount(count + 1)}
          style={{
            background: '#2563eb',
            color: '#fff',
            border: 'none',
            padding: '10px 24px',
            borderRadius: '6px',
            fontSize: '1rem',
            cursor: 'pointer',
            fontWeight: 'bold',
            transition: 'background 0.2s'
          }}
          onMouseOver={(e) => (e.currentTarget.style.background = '#1d4ed8')}
          onMouseOut={(e) => (e.currentTarget.style.background = '#2563eb')}
        >
          Zwiększ Licznik
        </button>
      </div>

      <p style={{ marginTop: '40px', fontSize: '0.9rem', color: '#64748b' }}>
        Edytuj <code>src/App.tsx</code> i zobacz automatyczne odświeżenie w przeglądarce.
      </p>
    </div>
  );
}
"""

    def _get_tsconfig_nextjs(self):
        return """{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
"""

    def _get_nextjs_page_tsx(self, title):
        return """import React from 'react';

export default function Home() {
  return (
    <main style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: '#09090b', color: '#fafafa', fontFamily: 'sans-serif' }}>
      <div style={{ maxWidth: '600px', padding: '24px', border: '1px solid #27272a', borderRadius: '12px', background: '#18181b', textAlign: 'center' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '12px' }}>""" + title + """ ✨</h1>
        <p style={{ color: '#a1a1aa', fontSize: '1rem', lineHeight: '1.6' }}>
          Starter Next.js z technologią App Router wygenerowany przez moduł Scaffolder.
        </p>
        <div style={{ display: 'inline-block', marginTop: '16px', padding: '8px 16px', background: '#27272a', borderRadius: '6px', color: '#f4f4f5', fontSize: '0.9rem' }}>
          Edytuj plik <code>src/app/page.tsx</code>
        </div>
      </div>
    </main>
  );
}
"""

    def _get_tsconfig_node(self):
        return """{
  "compilerOptions": {
    "target": "ES2021",
    "module": "CommonJS",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true
  },
  "include": ["src/**/*"]
}
"""

    def _get_express_index_ts(self, title):
        return """import express, { Request, Response } from 'express';
import cors from 'cors';

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

app.get('/', (req: Request, res: Response) => {
  res.json({
    message: "Witaj w Express.js Server API (" + title + ")",
    endpoints: {
      health: "/api/health",
      users: "/api/users"
    }
  });
});

app.get('/api/health', (req: Request, res: Response) => {
  res.status(200).json({
    status: "OK",
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

app.listen(PORT, () => {
  console.log(`[Server] Serwer Express działa pomyślnie pod adresem: http://localhost:${PORT}`);
});
"""

    def _get_laravel_controller(self):
        return """<?php

namespace App\\Http\\Controllers;

class HomeController
{
    public function index()
    {
        return [
            'framework' => 'Laravel 11',
            'status' => 'initialized',
            'server_time' => date('Y-m-d H:i:s'),
            'features' => [
                'Eloquent' => 'Zainstalowane',
                'Blade' => 'Zainstalowane',
                'Artisan' => 'Wspierany'
            ]
        ];
    }
}
"""

    def _get_symfony_controller(self):
        return """<?php

namespace App\\Controller;

use Symfony\\Component\\HttpFoundation\\JsonResponse;

class HomeController
{
    public function index(): JsonResponse
    {
        return new JsonResponse([
            'framework' => 'Symfony 7 Skeleton',
            'status' => 'UP',
            'details' => [
                'psr_compliant' => true,
                'micro_framework' => true
            ]
        ]);
    }
}
"""

    def _get_springboot_pom(self, name):
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.2.4</version>
    <relativePath/>
  </parent>
  <groupId>com.example</groupId>
  <artifactId>{name}</artifactId>
  <version>1.0.0-SNAPSHOT</version>
  <name>{name}</name>
  <description>Demo project built dynamically</description>
  <properties>
    <java.version>17</java.version>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
  </dependencies>
</project>
"""

    def _get_springboot_main(self):
        return """package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
        System.out.println("Spring Boot Web App zainicjalizowany pomyślnie.");
    }
}
"""

    def _get_springboot_controller(self):
        return """package com.example.demo.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.HashMap;
import java.util.Map;

@RestController
public class HelloController {

    @GetMapping("/")
    public Map<String, Object> index() {
        Map<String, Object> res = new HashMap<>();
        res.put("service", "Spring Boot Java App");
        res.put("status", "UP");
        res.put("documentation", "Auto-Generated by Project Scaffolder");
        return res;
    }
}
"""

    def _get_go_gin_main(self, title):
        return """package main

import (
	"net/http"
	"github.com/gin-gonic/gin"
)

func main() {
	r := gin.Default()

	r.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"app":     \"""" + title + """\",
			"engine":  "Gin Gonic (Golang)",
			"status":  "working",
			"routes":  []string{"GET /api/v1/health", "GET /api/v1/items/:id"},
		})
	})

	r.GET("/api/v1/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status": "healthy",
			"uptime": "100%",
		})
	})

	r.Run(":8080")
}
"""

    def _get_go_fiber_main(self, title):
        return """package main

import (
	"github.com/gofiber/fiber/v2"
)

func main() {
	app := fiber.New()

	app.Get("/", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"app":     \"""" + title + """\",
			"engine":  "Fiber Server (Go)",
			"status":  "healthy",
			"readme":  "Use go run main.go to start locally",
		})
	})

	app.Listen(":3000")
}
"""

    # Kubernetes / Github CI/CD
    def _get_github_actions_ci(self, lang):
        setup_steps = ""
        if lang == "python":
            setup_steps = "- name: Install dependencies\\n  run: pip install -r requirements.txt"
        elif lang == "javascript":
            setup_steps = "- name: Install dependencies\\n  run: npm install\\n- name: Build project\\n  run: npm run build --if-present"
        else:
            setup_steps = "- name: Run simple check\\n  run: echo 'CI configured'"

        return f"""name: Integration Pipeline

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  build_and_validate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout source code
        uses: actions/checkout@v3

      - name: Setup Runner Environment
        uses: actions/setup-node@v3
        with:
          node-version: 18

      {setup_steps}
"""

    def _get_dockerfile_python(self, module, port, run_cmd):
        return f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE {port}
CMD ["sh", "-c", "{run_cmd}"]
"""

    def _get_dockerfile_node(self, build_cmd, out_dir, port):
        return f"""# Stage 1: Build Web App
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN {build_cmd}

# Stage 2: Serve using Nginx
FROM nginx:1.25-alpine
COPY --from=builder /app/{out_dir} /usr/share/nginx/html
EXPOSE {port}
CMD ["nginx", "-g", "daemon off;"]
"""

    def _get_dockerfile_node_express(self, port):
        return f"""FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE {port}
CMD ["npm", "start"]
"""

    def _get_dockerfile_go(self, port):
        return f"""FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod ./
# COPY go.sum ./
RUN go mod download
COPY . .
RUN go build -o main .

FROM alpine:latest
WORKDIR /root/
COPY --from=builder /app/main .
EXPOSE {port}
CMD ["./main"]
"""

    def _get_docker_compose_yml(self, lang, framework):
        port = 8000
        if framework in ["springboot", "gin"]:
            port = 8080
        elif framework in ["react", "nextjs", "fiber"]:
            port = 3000
        elif framework in ["flask", "express"]:
            port = 5000

        return f"""version: '3.8'

services:
  web-service:
    build: .
    ports:
      - "{port}:{port}"
    environment:
      - NODE_ENV=production
      - PYTHON_ENV=production
      - APP_PORT={port}
    restart: unless-stopped
"""
