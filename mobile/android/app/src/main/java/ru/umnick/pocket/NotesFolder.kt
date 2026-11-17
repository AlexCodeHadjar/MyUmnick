package ru.umnick.pocket

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.DocumentsContract
import androidx.documentfile.provider.DocumentFile

/**
 * Папка обмена с ПК по MTP (S-24.6, ADR-0050): пользователь один раз выбирает `Documents/UmNick`,
 * доступ сохраняется (SAF). Телефон пишет `notes.jsonl`, ПК кладёт `from_pc.jsonl`.
 */
object NotesFolder {
    private const val PICK = 42
    private const val PREFS = "folder"
    private const val KEY = "tree"

    fun pick(activity: Activity) {
        val start = DocumentsContract.buildDocumentUri("com.android.externalstorage.documents", "primary:Documents")
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).putExtra(DocumentsContract.EXTRA_INITIAL_URI, start)
        activity.startActivityForResult(intent, PICK)
    }

    fun onPicked(activity: Activity, requestCode: Int, data: Intent?) {
        val uri = data?.data ?: return
        if (requestCode != PICK) return
        val flags = Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        activity.contentResolver.takePersistableUriPermission(uri, flags)
        activity.getSharedPreferences(PREFS, 0).edit().putString(KEY, uri.toString()).apply()
    }

    fun ready(context: Context): Boolean = folder(context) != null

    /** Записать весь блокнот в общую папку: ПК перечитывает его целиком при подключении. */
    fun mirror(context: Context, notebook: Notebook) {
        val dir = folder(context) ?: return
        val file = dir.findFile("notes.jsonl") ?: dir.createFile("application/octet-stream", "notes.jsonl") ?: return
        context.contentResolver.openOutputStream(file.uri, "wt")?.use { out ->
            out.write(notebook.all().joinToString("") { it.toJson() + "\n" }.toByteArray())
        }
    }

    /** Забрать заметки, которые ПК положил в `from_pc.jsonl`. */
    fun importFromPc(context: Context, notebook: Notebook): Int {
        val file = folder(context)?.findFile("from_pc.jsonl") ?: return 0
        val lines = context.contentResolver.openInputStream(file.uri)?.use { it.bufferedReader().readLines() }
            ?: return 0
        return notebook.merge(lines.mapNotNull(Notebook.Note::parse))
    }

    private fun folder(context: Context): DocumentFile? {
        val saved = context.getSharedPreferences(PREFS, 0).getString(KEY, null) ?: return null
        return DocumentFile.fromTreeUri(context, Uri.parse(saved))?.takeIf { it.canWrite() }
    }
}
