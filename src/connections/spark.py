import os
import sys
from pyspark.sql import SparkSession
from src.utils.logger import setup_logger

logger = setup_logger("spark_connection")

class SparkSessionManager:
    """
    Manages the lifecycle, environment variables, memory configs,
    and process safety settings for local PySpark cluster runs.
    """
    def __init__(self, app_name: str = "RAG-Ingestion-Pipeline", driver_memory: str = "4g"):
        self.app_name = app_name
        self.driver_memory = driver_memory
        self._spark = None
        
    def _apply_environment_safeguards(self) -> None:
        """
        Injects necessary settings to run PySpark safely on macOS and Apple Silicon
        with third-party native libraries (like PyTorch and Tokenizers).
        """
        logger.info("Applying macOS fork-safety and environment safeguards...")
        
        # 1. macOS Fork safety for PyTorch
        os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
        
        # 2. Prevent tokenizers deadlock issues inside executors
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        # 3. Enable worker faulthandler log traces
        os.environ["SPARK_PYTHON_WORKER_FAULTHANDLER_ENABLED"] = "true"
        
        # 4. Map worker python binary explicitly to the virtual env's python
        os.environ["PYSPARK_PYTHON"] = sys.executable
        os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
        
        # 5. Point Java variables correctly
        os.environ["JAVA_HOME"] = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
        os.environ["PATH"] = f"/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:{os.environ.get('PATH', '')}"

    def get_or_create_session(self) -> SparkSession:
        """
        Builds and initializes the Spark session under local[1] mode.
        """
        if self._spark is not None:
            return self._spark
            
        # Set all properties
        self._apply_environment_safeguards()
        
        logger.info(f"Starting PySpark session '{self.app_name}' (local[1] mode)...")
        self._spark = SparkSession.builder \
            .appName(self.app_name) \
            .master("local[1]") \
            .config("spark.driver.memory", self.driver_memory) \
            .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
            .config("spark.sql.execution.pyspark.udf.faulthandler.enabled", "true") \
            .config("spark.python.worker.faulthandler.enabled", "true") \
            .getOrCreate()
            
        logger.info("SparkSession initialized successfully.")
        return self._spark

    def stop_session(self) -> None:
        """
        Safely shuts down the active Spark context.
        """
        if self._spark is not None:
            logger.info("Stopping PySpark Session...")
            self._spark.stop()
            self._spark = None
            logger.info("SparkSession stopped.")
