"""
工具名: flutter_generator
显示名: Flutter Generator
描述: 生成一个基本的Flutter项目结构和示例代码。
标签: ["flutter", "code_generation", "mobile_app"]
"""

import os
import sys
from typing import Dict

# 设置 PROJECT_DIR 和 sys.path
PROJECT_DIR = "/path/to/project"
if PROJECT_DIR not in sys.path:
    sys.path.append(PROJECT_DIR)

SKILL_META = {
    "name": "flutter_generator",
    "display_name": "Flutter Generator",
    "description": "生成一个基本的Flutter项目结构和示例代码。",
    "tags": ["flutter", "code_generation", "mobile_app"]
}

def generate_flutter_project(project_name: str, directory: str) -> Dict[str, bool]:
    """
    生成一个新的Flutter项目。

    参数:
    project_name (str): 项目的名称。
    directory (str): 项目的保存目录。

    返回:
    dict: 包含 success 字段，指示操作是否成功。
    """
    try:
        # 创建项目目录
        os.makedirs(os.path.join(directory, project_name), exist_ok=True)
        
        # 创建基本的Flutter项目结构
        os.makedirs(os.path.join(directory, project_name, "lib"), exist_ok=True)
        os.makedirs(os.path.join(directory, project_name, "assets"), exist_ok=True)
        os.makedirs(os.path.join(directory, project_name, "android/app/src/main/res"), exist_ok=True)
        
        # 创建 main.dart 文件
        with open(os.path.join(directory, project_name, "lib", "main.dart"), "w") as f:
            f.write("""
void main() {
  runApp(MyApp());
}

import 'package:flutter/material.dart';

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter Demo',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: MyHomePage(title: 'Flutter Demo Home Page'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  MyHomePage({Key? key, required this.title}) : super(key: key);

  final String title;

  @override
  _MyHomePageState createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  int _counter = 0;

  void _incrementCounter() {
    setState(() {
      _counter++;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Text(
              'You have pushed the button this many times:',
            ),
            Text(
              '$_counter',
              style: Theme.of(context).textTheme.headline4,
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _incrementCounter,
        tooltip: 'Increment',
        child: Icon(Icons.add),
      ),
    );
  }
}
""")
        
        # 创建 AndroidManifest.xml
        with open(os.path.join(directory, project_name, "android", "app", "src", "main", "AndroidManifest.xml"), "w") as f:
            f.write("""
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.{}">
    <application
        android:name=".MyApplication"
        android:label="Flutter Demo"
        android:icon="@mipmap/ic_launcher">
        <activity
            android:name=".MainActivity"
            android:launchMode="singleTop"
            android:theme="@style/LaunchTheme"
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|smallestScreenSize|layoutDirection|fontScale|screenLayout|density|uiMode"
            android:hardwareAccelerated="true"
            android:windowSoftInputMode="adjustResize">
            <meta-data
                android:name="io.flutter.embedding.android.NormalTheme"
                android:resource="@style/NormalTheme"/>
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>
</manifest>
""".format(project_name))
        
        return {"success": True}
    except Exception as e:
        print(f"Error generating Flutter project: {e}")
        return {"success": False}

if __name__ == "__main__":
    # 自测代码
    result = generate_flutter_project("test_project", "/path/to/save")
    print(result)