        cursor = None
        cnxn = None

        try:
            sql_connection = SQLConnection()
            sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
            cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

            if cursor and cnxn:
                cursor.execute('SELECT TOP (1000) [id], [RecipeStructureName] FROM [RecipeDB].[dbo].[viewRecipeStructures]')
                rows = cursor.fetchall()

                for row in rows:
                    recipe_id, RecipeStructureName = row
                    item_id = self.treeview_select_structure.insert("", "end", values=(recipe_id, RecipeStructureName))

                if RecipeStructureName in recipe_struct_mapping.values():
                    recipe_struct_for_this_item = next((key for key, value in recipe_struct_mapping.items() if value == RecipeStructureName), None)
                    if recipe_struct_for_this_item:
                        id_mapping[recipe_struct_for_this_item] = item_id

            mapped_id = id_mapping.get(recipe_struct)
            if mapped_id:
                self.treeview_select_structure.selection_set(mapped_id)
            else:
                logger.warning(f"Error: No mapping for recipe_struct value {recipe_struct}")

        except pyodbc.Error as e:
            logger.warning(f"Error in database connection: {e}")

        except IndexError:
            logger.warning("Database credentials seem to be incomplete.")

        except Exception as e:
            logger.warning(f"An unexpected error occurred: {e}")

        finally:
            if cursor and cnxn:
                sql_connection.disconnect_from_database(cursor, cnxn)

